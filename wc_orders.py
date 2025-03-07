#!/usr/bin/env python3
"""
Script to fetch WooCommerce orders data from MySQL database.
"""

import os
import sys
import csv
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime
import argparse

# Load environment variables
load_dotenv()

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
        db_host = os.getenv(f"IP_{db_number}")
        db_name = os.getenv(f"DATABASE_NAME_{db_number}")
        db_user = os.getenv(f"DATABASE_USER_{db_number}")
        db_password = os.getenv(f"DATABASE_PASSWORD_{db_number}")
        
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

def fetch_woocommerce_orders(connection, table_prefix, days=None, start_date=None, end_date=None):
    """
    Fetch WooCommerce orders from the database.
    
    Args:
        connection: MySQL database connection
        table_prefix (str): WordPress table prefix
        days (int, optional): Number of days to look back for orders
        start_date (str, optional): Start date for order range (YYYY-MM-DD)
        end_date (str, optional): End date for order range (YYYY-MM-DD)
        
    Returns:
        list: List of dictionaries containing order data
    """
    cursor = connection.cursor(dictionary=True)
    
    # Build the date filter part of the query
    date_filter = ""
    if days:
        date_filter = f"AND p.post_date >= DATE_SUB(NOW(), INTERVAL {days} DAY)"
    elif start_date and end_date:
        date_filter = f"AND p.post_date BETWEEN '{start_date}' AND '{end_date}'"
    elif start_date:
        date_filter = f"AND p.post_date >= '{start_date}'"
    elif end_date:
        date_filter = f"AND p.post_date <= '{end_date}'"
    
    # SQL query to fetch WooCommerce orders
    query = f"""
    SELECT 
        p.ID as order_id,
        p.post_date as order_date,
        p.post_status as order_status,
        MAX(CASE WHEN pm.meta_key = '_billing_first_name' THEN pm.meta_value END) as billing_first_name,
        MAX(CASE WHEN pm.meta_key = '_billing_last_name' THEN pm.meta_value END) as billing_last_name,
        MAX(CASE WHEN pm.meta_key = '_billing_email' THEN pm.meta_value END) as billing_email,
        MAX(CASE WHEN pm.meta_key = '_billing_phone' THEN pm.meta_value END) as billing_phone,
        MAX(CASE WHEN pm.meta_key = '_order_total' THEN pm.meta_value END) as order_total,
        MAX(CASE WHEN pm.meta_key = '_payment_method_title' THEN pm.meta_value END) as payment_method
    FROM 
        {table_prefix}posts p
    JOIN 
        {table_prefix}postmeta pm ON p.ID = pm.post_id
    WHERE 
        p.post_type = 'shop_order'
        {date_filter}
    GROUP BY 
        p.ID
    ORDER BY 
        p.post_date DESC
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
            order['products'] = fetch_order_items(connection, table_prefix, order_id)
            
        cursor.close()
        print(f"Successfully fetched {len(orders)} orders with their products.")
        return orders
        
    except mysql.connector.Error as e:
        print(f"Error fetching orders: {e}")
        cursor.close()
        return []

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
        oi.order_item_id,
        oi.order_item_name as product_name,
        MAX(CASE WHEN oim.meta_key = '_product_id' THEN oim.meta_value END) as product_id,
        MAX(CASE WHEN oim.meta_key = '_variation_id' THEN oim.meta_value END) as variation_id,
        MAX(CASE WHEN oim.meta_key = '_qty' THEN oim.meta_value END) as quantity,
        MAX(CASE WHEN oim.meta_key = '_line_total' THEN oim.meta_value END) as line_total,
        MAX(CASE WHEN oim.meta_key = '_line_subtotal' THEN oim.meta_value END) as line_subtotal
    FROM 
        {table_prefix}woocommerce_order_items oi
    JOIN 
        {table_prefix}woocommerce_order_itemmeta oim ON oi.order_item_id = oim.order_item_id
    WHERE 
        oi.order_id = {order_id}
        AND oi.order_item_type = 'line_item'
    GROUP BY 
        oi.order_item_id
    """
    
    try:
        cursor.execute(query)
        items = cursor.fetchall()
        cursor.close()
        return items
    except mysql.connector.Error as e:
        print(f"Error fetching order items for order {order_id}: {e}")
        cursor.close()
        return []

def export_to_csv(orders, filename=None):
    """
    Export orders data to CSV file.
    
    Args:
        orders (list): List of dictionaries containing order data
        filename (str, optional): Output filename
        
    Returns:
        str: Path to the saved CSV file
    """
    if not orders:
        return None
        
    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"woocommerce_orders_{timestamp}.csv"
    
    # Create a flattened list for CSV export
    flattened_orders = []
    for order in orders:
        products = order.pop('products', [])
        if not products:
            # If no products, still include the order
            flattened_order = order.copy()
            flattened_order.update({
                'product_name': '',
                'product_id': '',
                'variation_id': '',
                'quantity': '',
                'line_total': ''
            })
            flattened_orders.append(flattened_order)
        else:
            # Create a row for each product in the order
            for product in products:
                flattened_order = order.copy()
                flattened_order.update({
                    'product_name': product.get('product_name', ''),
                    'product_id': product.get('product_id', ''),
                    'variation_id': product.get('variation_id', ''),
                    'quantity': product.get('quantity', ''),
                    'line_total': product.get('line_total', '')
                })
                flattened_orders.append(flattened_order)
    
    # Save to CSV
    if flattened_orders:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = flattened_orders[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_orders)
        
        print(f"Orders data exported to {filename}")
        return filename
    else:
        print("No data to export.")
        return None

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Fetch WooCommerce orders from MySQL database')
    parser.add_argument('--db', type=int, choices=[1, 2], default=1, help='Database to use (1 or 2)')
    parser.add_argument('--days', type=int, help='Number of days to look back for orders')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, help='Output CSV filename')
    parser.add_argument('--prefix', type=str, default='wp_', help='WordPress table prefix (default: wp_)')
    
    args = parser.parse_args()
    
    # Get database connection
    connection = get_db_connection(args.db)
    
    if not connection:
        return
    
    # Use the provided table prefix or default to wp_
    table_prefix = args.prefix
    
    print(f"Using table prefix: {table_prefix}")
    
    # Fetch orders
    orders = fetch_woocommerce_orders(
        connection, 
        table_prefix,
        days=args.days,
        start_date=args.start,
        end_date=args.end
    )
    
    # Export to CSV
    if orders:
        export_to_csv(orders, args.output)
    
    # Close connection
    if connection.is_connected():
        connection.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()