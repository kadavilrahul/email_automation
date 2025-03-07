#!/usr/bin/env python3
# product_recommendations.py

import os
import sys
import json
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("product_recommendations.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database settings from .env
IP_DATABASE = os.getenv('IP_DATABASE')
DOMAIN = os.getenv('DOMAIN')
DATABASE_NAME = os.getenv('DATABASE_NAME')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_TABLE_PREFIX = os.getenv('DATABASE_TABLE_PREFIX')

# WooCommerce API credentials - construct from database settings
WC_URL = f"https://{DOMAIN}"
WC_KEY = os.getenv('WC_KEY', '')  # You may need to set these separately
WC_SECRET = os.getenv('WC_SECRET', '')  # You may need to set these separately

# Email settings from .env file
SMTP_SERVER = os.getenv('SMTP_SERVER', 'webmail.silkroademart.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'admin@silkroademart.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'Karimpadam2#')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'admin@silkroademart.com')

# API key for Gemini (replacing Agno)
GEMINI_API_KEY = os.getenv('GEMINI_API')

class ProductRecommendationSystem:
    def __init__(self):
        self.wc_url = WC_URL
        self.wc_key = WC_KEY
        self.wc_secret = WC_SECRET
        self.gemini_api_key = GEMINI_API_KEY
        
    def get_woocommerce_data(self, endpoint, params=None):
        """
        Get data from WooCommerce API
        """
        url = f"{self.wc_url}/wp-json/wc/v3/{endpoint}"
        try:
            response = requests.get(url, auth=(self.wc_key, self.wc_secret), params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from WooCommerce: {e}")
            return None

    def get_recent_orders(self, days=30):
        """
        Get orders from the last specified days
        """
        date_from = (datetime.now() - timedelta(days=days)).isoformat()
        params = {
            'after': date_from,
            'per_page': 100
        }
        return self.get_woocommerce_data('orders', params)

    def get_product_details(self, product_id):
        """
        Get product details by ID
        """
        return self.get_woocommerce_data(f'products/{product_id}')

    def get_product_categories(self, product_id):
        """
        Get categories for a product
        """
        product = self.get_product_details(product_id)
        if product and 'categories' in product:
            return [category['id'] for category in product['categories']]
        return []

    def get_similar_products(self, product_id, limit=3):
        """
        Find similar products based on categories
        """
        product = self.get_product_details(product_id)
        if not product:
            return []
            
        # Get product categories
        category_ids = self.get_product_categories(product_id)
        if not category_ids:
            return []
            
        # Find products in the same categories
        similar_products = []
        for category_id in category_ids:
            params = {
                'category': category_id,
                'per_page': 10,
                'exclude': [product_id]  # Exclude the current product
            }
            products = self.get_woocommerce_data('products', params)
            if products:
                similar_products.extend(products)
                
        # Remove duplicates and limit results
        unique_products = []
        product_ids = set()
        for p in similar_products:
            if p['id'] not in product_ids:
                product_ids.add(p['id'])
                unique_products.append(p)
                if len(unique_products) >= limit:
                    break
                    
        return unique_products

    def get_user_activity(self, user_id=None, email=None, days=30):
        """
        Get user activity (viewed products) from WooCommerce
        This is a simplified version and would need to be adapted to your actual activity tracking system
        """
        # In a real implementation, you would query your activity tracking database
        # For this example, we'll just return recent orders as "activity"
        if user_id:
            params = {
                'customer': user_id,
                'after': (datetime.now() - timedelta(days=days)).isoformat()
            }
            return self.get_woocommerce_data('orders', params)
        elif email:
            # Search for customer by email
            customers = self.get_woocommerce_data('customers', {'email': email})
            if customers and len(customers) > 0:
                return self.get_user_activity(user_id=customers[0]['id'], days=days)
        return []

    def generate_recommendation_email(self, customer, products):
        """
        Generate personalized email content using Gemini API
        """
        if not products:
            return None, None
            
        customer_name = customer.get('first_name', 'Valued Customer')
        
        # Prepare product information for Gemini
        product_info = []
        for p in products:
            product_info.append({
                'name': p['name'],
                'price': p['price'],
                'description': p['short_description'],
                'url': p['permalink']
            })
        
        # Use Gemini API to generate personalized email content
        prompt = f"""
        Create a personalized product recommendation email for {customer_name}.
        The email should recommend the following products:
        {json.dumps(product_info, indent=2)}
        
        The email should:
        1. Have a friendly, personalized greeting
        2. Briefly introduce why we're recommending these products
        3. List each product with its name, a brief description, and price
        4. Include a call to action to visit our store
        5. Have a friendly sign-off
        
        Return the email subject line and body separately.
        """
        
        try:
            # Make a request to the Gemini API
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.gemini_api_key}'
            }
            
            payload = {
                'contents': [{
                    'parts': [{
                        'text': prompt
                    }]
                }]
            }
            
            response = requests.post(
                'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the generated text from the response
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Parse the response to extract subject and body
            lines = generated_text.split('\n')
            subject = lines[0].replace('Subject:', '').strip()
            body = '\n'.join(lines[2:])
            return subject, body
        except Exception as e:
            logger.error(f"Error generating email with Gemini API: {e}")
            
            # Fallback to a simple template if Gemini API fails
            subject = f"Products we think you'll love, {customer_name}!"
            
            body = f"""Hello {customer_name},

We thought you might be interested in these products based on your recent activity:

"""
            for p in products:
                body += f"- {p['name']} - ${p['price']}\n   {p['short_description']}\n   {p['permalink']}\n\n"
                
            body += """
We hope you find something you love!

Best regards,
Your Store Team
"""
            return subject, body

    def send_email(self, to_email, subject, body):
        """
        Send an email with the recommendations
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
                
            logger.info(f"Recommendation email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def process_customer_recommendations(self, days=30):
        """
        Main function to process all customers and send recommendations
        """
        # Get recent orders
        orders = self.get_recent_orders(days)
        if not orders:
            logger.info("No recent orders found")
            return
            
        # Process each order
        processed_customers = set()
        for order in orders:
            customer_id = order.get('customer_id')
            if not customer_id or customer_id in processed_customers:
                continue
                
            # Get customer details
            customer = self.get_woocommerce_data(f'customers/{customer_id}')
            if not customer or not customer.get('email'):
                continue
                
            # Get products from the order
            ordered_products = []
            for item in order.get('line_items', []):
                ordered_products.append(item.get('product_id'))
                
            # Get recommendations based on ordered products
            recommendations = []
            for product_id in ordered_products:
                similar = self.get_similar_products(product_id)
                for p in similar:
                    if p not in recommendations:
                        recommendations.append(p)
                        
            # Generate and send email
            if recommendations:
                subject, body = self.generate_recommendation_email(customer, recommendations[:3])
                if subject and body:
                    self.send_email(customer['email'], subject, body)
                    
            processed_customers.add(customer_id)
            logger.info(f"Processed recommendations for customer {customer_id}")

if __name__ == "__main__":
    try:
        recommender = ProductRecommendationSystem()
        recommender.process_customer_recommendations()
    except Exception as e:
        logger.error(f"Error in recommendation system: {e}")