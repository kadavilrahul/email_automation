#!/usr/bin/env python3
"""
Script to fetch and combine WooCommerce orders data and WP Activity data from MySQL database.
"""

import os
import sys
import csv
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime
import argparse
import json

# Load environment variables
load_dotenv()

# Configuration variables
IP = os.getenv("IP_DATABASE")
DOMAIN = os.getenv("DOMAIN")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_TABLE_PREFIX = os.getenv("DATABASE_TABLE_PREFIX", "wp_")  # Default to wp_ if not set
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

def get_db_connection(db_number=1):
    """
    Create a database connection based on environment variables.
    
    Args:
        db_number (int): Database number to connect to (1 or 2)
        
    Returns:
        mysql.connector.connection: Database connection object
    """
    try:
        # Get database credentials from environment variables
        db_host = os.getenv(f"IP_DATABASE")
        db_name = os.getenv(f"DATABASE_NAME")
        db_user = os.getenv(f"DATABASE_USER")
        db_password = os.getenv(f"DATABASE_PASSWORD")
        
        print(f"Connecting to database: {db_name} at {db_host} with user {db_user}")
        
        # Connect to the database
        connection = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        if connection.is_connected():
            print(f"Connected to MySQL database: {db_name}")
            return connection
            
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL database: {e}")
        sys.exit(1)

def fetch_order_items(connection, table_prefix, order_id):
    """
    Fetch line items (products) for a specific order.
    
    Args:
        connection: MySQL database connection
        table_prefix (str): WordPress table prefix
        order_id (int): Order ID to fetch items for
        
    Returns:
        list: List of dictionaries containing order item data
    """
    cursor = connection.cursor(dictionary=True)
    
    # Query to get order items
    query = f"""
    SELECT 
        oi.order_item_name as product_name,
        oim.meta_value as product_id
    FROM 
        {table_prefix}woocommerce_order_items oi
    JOIN
        {table_prefix}woocommerce_order_itemmeta oim ON oi.order_item_id = oim.order_item_id
    WHERE 
        oi.order_id = {order_id}
        AND oi.order_item_type = 'line_item'
        AND oim.meta_key = '_product_id'
    """
    
    try:
        cursor.execute(query)
        items = cursor.fetchall()
        cursor.close()
        
        product_data = [(item['product_name'], item['product_id']) for item in items]
        return product_data
    except mysql.connector.Error as e:
        print(f"Error fetching order items for order {order_id}: {e}")
        cursor.close()
        return []

def fetch_woocommerce_orders(connection, table_prefix, limit=20):
    """
    Fetch WooCommerce orders from the database.
    
    Args:
        connection: MySQL database connection
        table_prefix (str): WordPress table prefix
        limit (int, optional): Maximum number of orders to fetch. Default is 20.
        
    Returns:
        list: List of dictionaries containing order data
    """
    cursor = connection.cursor(dictionary=True)
    
    # SQL query to fetch WooCommerce orders
    query = f"""
    SELECT 
        p.ID as order_id,
        p.post_date as order_date,
        p.post_status as order_status,
        MAX(CASE WHEN pm.meta_key = '_billing_first_name' THEN pm.meta_value END) as billing_first_name,
        MAX(CASE WHEN pm.meta_key = '_billing_last_name' THEN pm.meta_value END) as billing_last_name,
        MAX(CASE WHEN pm.meta_key = '_billing_email' THEN pm.meta_value END) as billing_email,
        MAX(CASE WHEN pm.meta_key = '_billing_phone' THEN pm.meta_value END) as billing_phone
    FROM 
        {table_prefix}posts p
    JOIN 
        {table_prefix}postmeta pm ON p.ID = pm.post_id
    WHERE 
        p.post_type = 'shop_order'
    GROUP BY 
        p.ID
    ORDER BY 
        p.post_date DESC
    LIMIT {limit}
    """
    
    try:
        cursor.execute(query)
        orders = cursor.fetchall()
        
        if not orders:
            print("No orders found for the specified criteria.")
            cursor.close()
            return []
        
        # Fetch order items for each order
        for order in orders:
            order_id = order['order_id']
            product_data = fetch_order_items(connection, table_prefix, order_id)
            if product_data:
                order['product_name'] = ", ".join([item[0] for item in product_data])
                order['product_id'] = ", ".join([item[1] for item in product_data])
            else:
                order['product_name'] = ""
                order['product_id'] = ""
        
        cursor.close()
        print(f"Successfully fetched {len(orders)} orders.")
        return orders
        
    except mysql.connector.Error as e:
        print(f"Error fetching orders: {e}")
        cursor.close()
        return []

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

def fetch_activity_log(connection, table_prefix, limit=20):
    """
    Fetch activity log entries from the database.
    
    Args:
        connection: MySQL database connection
        table_prefix (str): WordPress table prefix
        limit (int, optional): Maximum number of activity log entries to fetch. Default is 20.
        
    Returns:
        list: List of dictionaries containing activity log data
    """
    cursor = connection.cursor(dictionary=True)
    
    # Table names
    wsal_occurrences = f"{table_prefix}wsal_occurrences"
    wsal_metadata = f"{table_prefix}wsal_metadata"
    
    # Get available columns in the occurrences table
    occurrence_columns = [
        'o.id', 
        'o.alert_id', 
        'o.created_on', 
        'u.user_login', 
        'u.user_email'
    ]
    
    # Build the query
    query = f"""
    SELECT 
        {', '.join(occurrence_columns)}
    FROM {wsal_occurrences} o
    LEFT JOIN {table_prefix}users u ON o.user_id = u.ID
    WHERE o.alert_id = 9073
    ORDER BY o.created_on DESC LIMIT {limit}
    """
    
    try:
        cursor.execute(query)
        records = cursor.fetchall()
        
        if not records:
            print("No activity log entries found.")
            cursor.close()
            return []
        
        # Extract product name from metadata
        for record in records:
            metadata = extract_metadata(record['id'], cursor, table_prefix)
            record['product_name'] = metadata.get("ProductTitle", "")
        
        cursor.close()
        print(f"Successfully fetched {len(records)} activity log entries.")
        return records
        
    except mysql.connector.Error as e:
        print(f"Error fetching activity log entries: {e}")
        cursor.close()
        return []

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Fetch and combine WooCommerce orders data and WP Activity data from MySQL database')
    parser.add_argument('--output', type=str, help='Output CSV filename')
    args = parser.parse_args()
    
    # Get database connection
    connection = get_db_connection()
    
    if not connection:
        return
    
    # Table prefix
    table_prefix = os.getenv('DATABASE_TABLE_PREFIX', 'wp_')
    
    # Fetch WooCommerce orders
    orders = fetch_woocommerce_orders(connection, table_prefix)
    
    # Fetch activity log entries
    activity_log = fetch_activity_log(connection, table_prefix)
    
    # Combine data into desired format
    formatted_data = []
    if orders:
        for order in orders:
            formatted_data.append({
                'email': order.get('billing_email', ''),
                'product_name': order.get('product_name', ''),
                'timestamp': order.get('order_date', ''),
                'type': 'order'
            })
    if activity_log:
        for activity in activity_log:
            formatted_data.append({
                'email': activity.get('user_email', ''),
                'product_name': activity.get('product_name', ''),
                'timestamp': format_timestamp(activity.get('created_on', '')),
                'type': 'view'
            })

    # Export to CSV
    if formatted_data:
        filename = args.output if args.output else "combined_data.csv"
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['email', 'product_name', 'timestamp', 'type']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(formatted_data)
        print(f"Combined data exported to {filename}")
    else:
        print("No data to export.")
    
    # Close connection
    if connection.is_connected():
        connection.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()
