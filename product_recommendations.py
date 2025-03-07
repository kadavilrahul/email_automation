#!/usr/bin/env python3
# product_recommendations.py

import os
import sys
import json
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

# Email settings from .env file
SMTP_SERVER = os.getenv('SMTP_SERVER', 'webmail.silkroademart.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'admin@silkroademart.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'Karimpadam2#')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'admin@silkroademart.com')

# API key for Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API')

class ProductRecommendationSystem:
    def __init__(self):
        self.gemini_api_key = GEMINI_API_KEY
        
    def generate_recommendation_email(self, customer, original_product, recommended_products):
        """
        Generate personalized email content using Gemini API
        """
        if not recommended_products:
            return None, None
            
        customer_name = customer.get('first_name', 'Valued Customer')
        
        # Prepare product information for Gemini
        original_product_info = {
            'name': original_product['name'],
            'price': original_product['price'],
            'description': original_product['description']
        }
        
        recommended_product_info = []
        for p in recommended_products:
            recommended_product_info.append({
                'name': p['name'],
                'price': p['price'],
                'description': p['description']
            })
        
        # Use Gemini API to generate personalized email content
        prompt = f"""
        Create a personalized product recommendation email for {customer_name}.
        The customer recently purchased:
        {json.dumps(original_product_info, indent=2)}
        
        We want to recommend these similar products:
        {json.dumps(recommended_product_info, indent=2)}
        
        The email should:
        1. Have a friendly, personalized greeting
        2. Mention the original product they purchased
        3. Introduce the recommended products and why they might be interested
        4. List each recommended product with its name, description, and price
        5. Include a call to action to view these products
        6. Have a friendly sign-off
        
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
            subject = f"Products you might love, {customer_name}!"
            
            body = f"""Hello {customer_name},

We noticed you recently purchased the {original_product['name']} and thought you might be interested in these similar products:

"""
            for p in recommended_products:
                body += f"- {p['name']} - ${p['price']}\n   {p['description']}\n\n"
                
            body += """
Check them out and see if they catch your eye!

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
            
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
                
            logger.info(f"Recommendation email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def get_recommendations(self, original_product, all_products):
        """
        Get product recommendations based on the original product
        This is a simple recommendation logic that can be replaced with more sophisticated methods
        """
        # Simple recommendation logic - find products in the same category or with similar characteristics
        recommendations = []
        for product in all_products:
            # Exclude the original product
            if product['name'] != original_product['name']:
                # You can add more sophisticated matching logic here
                # For now, we'll just take the first 3 different products
                recommendations.append(product)
                if len(recommendations) >= 3:
                    break
        
        return recommendations

    def send_product_recommendation(self, customer, original_product, all_products):
        """
        Main method to send product recommendations
        """
        try:
            # Get recommendations based on the original product
            recommended_products = self.get_recommendations(original_product, all_products)
            
            # Generate and send email
            if recommended_products:
                subject, body = self.generate_recommendation_email(
                    customer, 
                    original_product, 
                    recommended_products
                )
                
                if subject and body:
                    # Send email from admin@silkroademart.com to the customer
                    self.send_email(customer['email'], subject, body)
                    logger.info(f"Sent recommendation email to {customer['email']}")
                    return True
            
            logger.info("No recommendations found")
            return False
        
        except Exception as e:
            logger.error(f"Error in sending product recommendation: {e}")
            return False

if __name__ == "__main__":
    try:
        # Create a recommendation system instance
        recommender = ProductRecommendationSystem()
        
        # Define the customer
        customer = {
            'first_name': 'Rahul',
            'last_name': 'Dinesh',
            'email': 'kadavil.rahul@gmail.com'  # Using a domain-specific email
        }
        
        # Define the original product the customer ordered
        original_product = {
            'name': 'Wireless Bluetooth Headphones',
            'price': 79.99,
            'description': 'High-quality wireless headphones with noise cancellation'
        }
        
        # Define a list of all available products 
        all_products = [
            {
                'name': 'Wireless Bluetooth Headphones',
                'price': 79.99,
                'description': 'High-quality wireless headphones with noise cancellation'
            },
            {
                'name': 'Over-Ear Studio Headphones',
                'price': 129.99,
                'description': 'Professional-grade studio headphones with superior sound quality'
            },
            {
                'name': 'Noise-Cancelling Earbuds',
                'price': 99.99,
                'description': 'Compact wireless earbuds with advanced noise cancellation technology'
            },
            {
                'name': 'Portable Bluetooth Speaker',
                'price': 59.99,
                'description': 'Compact and powerful wireless speaker with long battery life'
            }
        ]
        
        # Send product recommendation
        result = recommender.send_product_recommendation(customer, original_product, all_products)
        
        # Print result for verification
        if result:
            print("Recommendation email sent successfully!")
        else:
            print("Failed to send recommendation email.")
    
    except Exception as e:
        logger.error(f"Error in recommendation system: {e}")
        print(f"An error occurred: {e}")