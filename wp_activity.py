import os
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime
import argparse
import csv
import json

# Load environment variables
load_dotenv()

# Configuration variables
IP = os.getenv("IP_DATABASE")
DOMAIN = os.getenv("DOMAIN")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_TABLE_PREFIX = os.getenv("DATABASE_TABLE_PREFIX", "wp_")  # Default to kdf_ if not set
DEFAULT_ACTIVITY_LIMIT = 5  # Default number of activities to display

# Mapping of common event IDs to descriptions
EVENT_DESCRIPTIONS = {
    9073: "User viewed a product"
}

def format_timestamp(timestamp):
    """Convert timestamp to readable datetime"""
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(timestamp)

def diagnose_wsal_tables(cursor):
    """Diagnose the structure of WP Security Audit Log tables"""
    print("\n--- WP Security Audit Log Table Diagnosis ---")
    
    # Check tables
    tables_to_check = ['wp_wsal_occurrences', 'wp_wsal_metadata']
    
    for table in tables_to_check:
        print(f"\nTable: {table}")
        
        # Get table columns
        try:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            print("Columns:")
            for col in columns:
                print(f"  - {col['Field']} ({col['Type']})")
        except Exception as e:
            print(f"Error describing table {table}: {e}")
        
        # Get sample data
        try:
            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
            sample_data = cursor.fetchall()
            print("\nSample Data:")
            for row in sample_data:
                print(row)
        except Exception as e:
            print(f"Error fetching sample data from {table}: {e}")
    
    # Check for any custom event IDs
    try:
        cursor.execute("SELECT DISTINCT alert_id FROM wp_wsal_occurrences ORDER BY alert_id")
        unique_events = cursor.fetchall()
        print("\nUnique Event IDs:")
        for event in unique_events:
            print(f"  - {event['alert_id']}")
    except Exception as e:
        print(f"Error fetching unique event IDs: {e}")

def extract_metadata(occurrence_id, cursor, table_prefix='kdf_'):
    """Extract metadata for a specific occurrence with detailed error handling"""
    metadata_table = f"{table_prefix}wsal_metadata"
    try:
        # First, check if any metadata exists for this occurrence
        cursor.execute(f"SELECT COUNT(*) as metadata_count FROM {metadata_table} WHERE occurrence_id = %s", (occurrence_id,))
        count_result = cursor.fetchone()
        metadata_count = count_result['metadata_count'] if count_result else 0
        
        if metadata_count == 0:
            # No metadata found, but this isn't necessarily an error
            return {}
        
        # If metadata exists, retrieve it
        cursor.execute(f"""
            SELECT name, value 
            FROM {metadata_table} 
            WHERE occurrence_id = %s
        """, (occurrence_id,))
        
        metadata = {}
        for row in cursor.fetchall():
            # Ensure we're working with strings
            try:
                name = row['name'].decode('utf-8') if isinstance(row['name'], bytes) else str(row['name'])
                value = row['value'].decode('utf-8') if isinstance(row['value'], bytes) else str(row['value'])
                metadata[name] = value
            except Exception as conversion_error:
                print(f"Error converting metadata for occurrence {occurrence_id}: {conversion_error}")
                print(f"Raw data - Name: {row['name']}, Value: {row['value']}")
        
        return metadata
    except Exception as e:
        print(f"Detailed error extracting metadata for occurrence {occurrence_id}: {e}")
        return {}

def get_table_columns(cursor, table_name):
    """Retrieve the columns of a given table"""
    try:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        return [col['Field'] for col in columns]
    except Exception as e:
        print(f"Error retrieving columns for {table_name}: {e}")
        return []

def check_tables_exist(cursor):
    """Check if the required tables exist in the database"""
    print("Checking for activity log tables...")
    
    # Common table prefixes to check
    prefixes = ['wp_', 'wp_wsal_', '']
    
    # Tables to look for (without prefix)
    tables_to_find = {
        'occurrences': False,
        'metadata': False
    }
    
    # Store the actual table names when found
    found_tables = {}
    
    # Get all tables in the database
    cursor.execute("SHOW TABLES")
    all_tables = [table[0] for table in cursor.fetchall()]
    print(f"Found {len(all_tables)} tables in database")
    
    # Check for each possible table name
    for prefix in prefixes:
        for table_base in tables_to_find.keys():
            for table in all_tables:
                possible_name = f"{prefix}{table_base}"
                if table.lower() == possible_name.lower() or table.lower().endswith(f"_{table_base}".lower()):
                    tables_to_find[table_base] = True
                    found_tables[table_base] = table
                    print(f"Found {table_base} table: {table}")
    
    # Check if we found all required tables
    all_found = all(tables_to_find.values())
    
    if not all_found:
        missing = [table for table, found in tables_to_find.items() if not found]
        print(f"Missing required tables: {', '.join(missing)}")
        print("Available tables:")
        for table in sorted(all_tables):
            print(f"  - {table}")
    
    return all_found, found_tables

def main():
    # Setup argument parsing
    parser = argparse.ArgumentParser(description='Extract detailed activity log from WordPress')
    parser.add_argument('--limit', type=int, default=DEFAULT_ACTIVITY_LIMIT, help=f'Number of records to retrieve (default: {DEFAULT_ACTIVITY_LIMIT})')
    parser.add_argument('--days', type=int, help='Show events from the last X days')
    parser.add_argument('--event', type=int, default=9073, help='Filter by specific event ID (default: 9073 - User viewed a product)')
    parser.add_argument('--user', type=str, help='Filter by username or user ID')
    parser.add_argument('--csv', type=str, help='Export results to CSV file')
    parser.add_argument('--diagnose', action='store_true', help='Run table diagnostic information')
    parser.add_argument('--prefix', type=str, default=DATABASE_TABLE_PREFIX, help=f'Database table prefix (default: {DATABASE_TABLE_PREFIX})')
    args = parser.parse_args()

    try:
        # Establish database connection
        connection = mysql.connector.connect(
            host=IP,
            database=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            
            # Run diagnostic if requested
            if args.diagnose:
                # Show all tables in the database
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                print(f"Found {len(tables)} tables in database {DATABASE_NAME}:")
                for table in tables:
                    print(f"  - {list(table.values())[0]}")
                return
            
            # Check if WP Security Audit Log tables exist
            table_prefix = args.prefix
            wsal_occurrences = f"{table_prefix}wsal_occurrences"
            wsal_metadata = f"{table_prefix}wsal_metadata"
            
            # Check if the tables exist
            cursor.execute(f"SHOW TABLES LIKE '{wsal_occurrences}'")
            occurrences_exists = cursor.fetchone() is not None
            
            cursor.execute(f"SHOW TABLES LIKE '{wsal_metadata}'")
            metadata_exists = cursor.fetchone() is not None
            
            if not occurrences_exists:
                print(f"Table {wsal_occurrences} does not exist. Looking for product view data in other tables...")
                
                # Query for product views in WooCommerce tables
                posts_table = f"{table_prefix}posts"
                postmeta_table = f"{table_prefix}postmeta"
                
                # Check if these tables exist
                cursor.execute(f"SHOW TABLES LIKE '{posts_table}'")
                posts_exists = cursor.fetchone() is not None
                
                cursor.execute(f"SHOW TABLES LIKE '{postmeta_table}'")
                postmeta_exists = cursor.fetchone() is not None
                
                if posts_exists and postmeta_exists:
                    # Query for recently viewed products
                    query = f"""
                    SELECT p.ID, p.post_title, p.post_date, p.post_modified, 
                           u.user_login, u.user_email
                    FROM {posts_table} p
                    LEFT JOIN {postmeta_table} pm ON p.ID = pm.post_id
                    LEFT JOIN {table_prefix}users u ON pm.meta_value = u.ID
                    WHERE p.post_type = 'product'
                    AND pm.meta_key LIKE '%viewed%'
                    ORDER BY p.post_modified DESC
                    LIMIT %s
                    """
                    
                    try:
                        cursor.execute(query, (args.limit,))
                        products = cursor.fetchall()
                        
                        if products:
                            print(f"Found {len(products)} recently viewed products:")
                            print("-" * 100)
                            
                            for product in products:
                                print(f"Product ID: {product['ID']}")
                                print(f"Title: {product['post_title']}")
                                print(f"Last Modified: {product['post_modified']}")
                                if product['user_login']:
                                    print(f"Viewed by: {product['user_login']} ({product['user_email']})")
                                print("-" * 100)
                        else:
                            # Try a different approach - get product view count
                            query = f"""
                            SELECT p.ID, p.post_title, pm.meta_key, pm.meta_value
                            FROM {posts_table} p
                            JOIN {postmeta_table} pm ON p.ID = pm.post_id
                            WHERE p.post_type = 'product'
                            AND (
                                pm.meta_key LIKE '%view%count%' OR
                                pm.meta_key LIKE '%product_views%' OR
                                pm.meta_key LIKE '%total_sales%'
                            )
                            ORDER BY CAST(pm.meta_value AS UNSIGNED) DESC
                            LIMIT %s
                            """
                            
                            cursor.execute(query, (args.limit,))
                            products = cursor.fetchall()
                            
                            if products:
                                print(f"Found {len(products)} products with view/sales data:")
                                print("-" * 100)
                                
                                for product in products:
                                    print(f"Product ID: {product['ID']}")
                                    print(f"Title: {product['post_title']}")
                                    print(f"Metric: {product['meta_key']}")
                                    print(f"Value: {product['meta_value']}")
                                    print("-" * 100)
                            else:
                                print("No product view data found in the database.")
                    except Exception as e:
                        print(f"Error querying product view data: {e}")
                else:
                    print(f"WooCommerce tables not found. Available tables:")
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    for table in tables:
                        print(f"  - {list(table.values())[0]}")
                
                return
            
            # If we get here, the WSAL tables exist, so proceed with the original query
            # Get available columns in the occurrences table
            occurrence_columns = get_table_columns(cursor, wsal_occurrences)
            
            # Dynamically build the select columns
            select_columns = [
                'o.id', 
                'o.alert_id', 
                'o.created_on', 
                'o.user_id', 
                'u.user_login', 
                'u.user_email'
            ]
            
            # Add optional columns if they exist
            optional_columns = {
                'site_id': 'o.site_id',
                'blog_id': 'o.blog_id',
                'object_id': 'o.object_id',
                'severity': 'o.severity'
            }
            
            for col_name, col_ref in optional_columns.items():
                if col_name in occurrence_columns:
                    select_columns.append(col_ref)
            
            # Build the query
            query = f"""
            SELECT 
                {', '.join(select_columns)}
            FROM {wsal_occurrences} o
            LEFT JOIN {table_prefix}users u ON o.user_id = u.ID
            """
            
            # Prepare WHERE clauses and parameters
            where_clauses = []
            params = []
            
            # Filter by days
            if args.days:
                where_clauses.append("o.created_on > UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL %s DAY))")
                params.append(args.days)
            
            # Filter by event ID
            if args.event:
                where_clauses.append("o.alert_id = %s")
                params.append(args.event)
            
            # Filter by user
            if args.user:
                # Check if it's a numeric user ID or a username
                if args.user.isdigit():
                    where_clauses.append("o.user_id = %s")
                else:
                    where_clauses.append("u.user_login = %s")
                params.append(args.user)
            
            # Combine WHERE clauses
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Order and limit
            query += " ORDER BY o.created_on DESC LIMIT %s"
            params.append(args.limit)
            
            # Execute the query
            print("Executing query:", query)
            print("Parameters:", params)
            
            cursor.execute(query, params)
            records = cursor.fetchall()
            
            # Prepare CSV if requested
            csv_file = None
            csv_writer = None
            if args.csv:
                csv_file = open(args.csv, 'w', newline='', encoding='utf-8')
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow([
                    'Timestamp', 'Event ID', 'Event Description', 
                    'User', 'User Email', 'Details', 
                    'EditorLinkProduct', 'ProductStatus', 'ProductTitle', 'ProductUrl', 'SKU',
                    'Site ID', 'Blog ID', 'Object ID', 'Severity'
                ])
            
            # Process and display records
            print(f"Found {len(records)} activity log entries:")
            print("-" * 100)
            
            for record in records:
                # Get occurrence details
                occurrence_id = record['id']
                alert_id = record['alert_id']
                created_on = format_timestamp(record['created_on'])
                user_login = record.get('user_login', 'Unknown')
                user_email = record.get('user_email', '')
                
                # Get event description
                event_description = EVENT_DESCRIPTIONS.get(
                    alert_id, 
                    f"Unknown Event (ID: {alert_id})"
                )
                
                # Attempt to extract metadata
                metadata = {}
                if metadata_exists:
                    try:
                        metadata = extract_metadata(occurrence_id, cursor, table_prefix)
                    except Exception as meta_error:
                        print(f"Error extracting metadata for occurrence {occurrence_id}: {meta_error}")
                
                # Extract metadata values
                editor_link_product = metadata.get("EditorLinkProduct", "")
                product_status = metadata.get("ProductStatus", "")
                product_title = metadata.get("ProductTitle", "")
                product_url = metadata.get("ProductUrl", "")
                sku = metadata.get("SKU", "")
                
                # Write to CSV if requested
                if csv_writer:
                    csv_writer.writerow([
                        created_on,
                        alert_id,
                        event_description,
                        user_login,
                        user_email,
                        json.dumps(metadata) if metadata else '',
                        editor_link_product,
                        product_status,
                        product_title,
                        product_url,
                        sku,
                        record.get('site_id', ''),
                        record.get('blog_id', ''),
                        record.get('object_id', ''),
                        record.get('severity', '')
                    ])
                
                print("-" * 100)
            
            # Close CSV file if opened
            if csv_file:
                csv_file.close()
                print(f"CSV export completed: {args.csv}")
            
            # Export to CSV if there are records and --csv is not specified
            if records and not args.csv:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"wp_activity_{timestamp}.csv"
                
                # Prepare CSV data
                csv_data = []
                for record in records:
                    # Get occurrence details
                    occurrence_id = record['id']
                    alert_id = record['alert_id']
                    created_on = format_timestamp(record['created_on'])
                    user_login = record.get('user_login', 'Unknown')
                    user_email = record.get('user_email', '')
                    
                    # Get event description
                    event_description = EVENT_DESCRIPTIONS.get(
                        alert_id, 
                        f"Unknown Event (ID: {alert_id})"
                    )
                    
                    # Attempt to extract metadata
                    metadata = {}
                    if metadata_exists:
                        try:
                            metadata = extract_metadata(occurrence_id, cursor, table_prefix)
                        except Exception as meta_error:
                            print(f"Error extracting metadata for occurrence {occurrence_id}: {meta_error}")
                    
                    # Extract metadata values
                    editor_link_product = metadata.get("EditorLinkProduct", "")
                    product_status = metadata.get("ProductStatus", "")
                    product_title = metadata.get("ProductTitle", "")
                    product_url = metadata.get("ProductUrl", "")
                    sku = metadata.get("SKU", "")
                    
                    csv_data.append([
                        created_on,
                        alert_id,
                        event_description,
                        user_login,
                        user_email,
                        json.dumps(metadata) if metadata else '',
                        editor_link_product,
                        product_status,
                        product_title,
                        product_url,
                        sku,
                        record.get('site_id', ''),
                        record.get('blog_id', ''),
                        record.get('object_id', ''),
                        record.get('severity', '')
                    ])
                
                # Write to CSV
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow([
                        'Timestamp', 'Event ID', 'Event Description', 
                        'User', 'User Email', 'Details', 
                        'EditorLinkProduct', 'ProductStatus', 'ProductTitle', 'ProductUrl', 'SKU',
                        'Site ID', 'Blog ID', 'Object ID', 'Severity'
                    ])
                    csv_writer.writerows(csv_data)
                
                print(f"CSV export completed: {filename}")

    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("Database connection closed")

if __name__ == "__main__":
    main()
