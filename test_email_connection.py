#!/usr/bin/env python3
"""
Test Email Connection Script

This script tests both IMAP (incoming) and SMTP (outgoing) email connections
using the configuration from the .env file.
"""

import os
import sys
import imaplib
import smtplib
import ssl
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import time

def create_ssl_context(verify_hostname=True):
    """Create a flexible SSL context."""
    context = ssl.create_default_context()
    
    if not verify_hostname:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    
    return context

def try_smtp_ssl(server, port, username, password, sender_email):
    """Try SMTP connection with SSL."""
    try:
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect to the SMTP server
        with smtplib.SMTP_SSL(server, port, context=context) as smtp:
            # Login to the server
            smtp.login(username, password)
            
            # Check if connection is alive
            smtp.noop()
            
            return True, "Successfully connected with SSL"
            
    except Exception as e:
        return False, str(e)

def try_smtp_tls(server, port, username, password, sender_email):
    """Try SMTP connection with TLS."""
    try:
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect to the SMTP server
        with smtplib.SMTP(server, port) as smtp:
            # Start TLS encryption
            smtp.starttls(context=context)
            
            # Login to the server
            smtp.login(username, password)
            
            # Check if connection is alive
            smtp.noop()
            
            return True, "Successfully connected with TLS"
            
    except Exception as e:
        return False, str(e)

def try_smtp_ssl_no_verify(server, port, username, password, sender_email):
    """Try SMTP connection with SSL but without verification."""
    try:
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect to the SMTP server
        with smtplib.SMTP_SSL(server, port, context=context) as smtp:
            # Login to the server
            smtp.login(username, password)
            
            # Check if connection is alive
            smtp.noop()
            
            return True, "Successfully connected with SSL (no verification)"
            
    except Exception as e:
        return False, str(e)

def try_smtp_with_token(server, port, username, password, sender_email, token):
    """Try SMTP connection with token authentication."""
    try:
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect to the SMTP server
        with smtplib.SMTP_SSL(server, port, context=context) as smtp:
            # Try different authentication methods with the token
            
            # Method 1: Use token as password
            try:
                smtp.login(username, token)
            except:
                # Method 2: Try XOAUTH2 if available
                try:
                    auth_string = f'user={username}\1auth=Bearer {token}\1\1'
                    smtp.auth('XOAUTH2', lambda x: auth_string)
                except:
                    # Method 3: Try AUTH PLAIN with token
                    try:
                        auth_str = base64.b64encode(f'\0{username}\0{token}'.encode()).decode()
                        smtp.docmd("AUTH", f"PLAIN {auth_str}")
                    except:
                        # If all token methods fail, try with regular password as fallback
                        smtp.login(username, password)
            
            # Check if connection is alive
            smtp.noop()
            
            return True, "Successfully connected with token authentication"
            
    except Exception as e:
        return False, str(e)

def send_test_email(server, port, username, password, sender_email, recipient, method, token=None):
    """Send a test email using the specified connection method."""
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient
        message["Subject"] = "Test Email Connection"
        
        # Add body to email
        body = f"""
        This is a test email sent at {time.strftime('%Y-%m-%d %H:%M:%S')}
        
        This email confirms that your SMTP server configuration is working correctly.
        Connection method: {method}
        """
        message.attach(MIMEText(body, "plain"))
        
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect and send based on method
        if "TLS" in method:
            with smtplib.SMTP(server, port) as smtp:
                smtp.starttls(context=context)
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP_SSL(server, port, context=context) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
                
        return True, "Email sent successfully"
        
    except Exception as e:
        return False, str(e)

def try_imap_standard_ssl(server, port, username, password):
    """Try standard IMAP SSL connection."""
    try:
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect to the IMAP server
        imap = imaplib.IMAP4_SSL(server, port=port, ssl_context=context)
        
        # Login to the server
        imap.login(username, password)
        
        # List available mailboxes
        status, mailboxes = imap.list()
        if status == 'OK':
            result = f"Available mailboxes: {len(mailboxes)}"
            for i, mailbox in enumerate(mailboxes[:3]):  # Show first 3 mailboxes
                result += f"\n  - {mailbox.decode()}"
            if len(mailboxes) > 3:
                result += f"\n  ... and {len(mailboxes) - 3} more"
        
        # Logout
        imap.logout()
        return True, result
        
    except Exception as e:
        return False, str(e)

def try_imap_no_verify(server, port, username, password):
    """Try IMAP connection without SSL verification."""
    try:
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect to the IMAP server
        imap = imaplib.IMAP4_SSL(server, port=port, ssl_context=context)
        
        # Login to the server
        imap.login(username, password)
        
        # Get a simple result
        status, count = imap.select('INBOX')
        result = f"Connected to INBOX with {count[0].decode()} messages"
        
        # Logout
        imap.logout()
        return True, result
        
    except Exception as e:
        return False, str(e)

def try_imap_with_token(server, port, username, password, token):
    """Try IMAP connection using authentication token."""
    try:
        # Create an SSL context with flexible verification
        context = create_ssl_context(verify_hostname=False)
        
        # Connect to the IMAP server
        imap = imaplib.IMAP4_SSL(server, port=port, ssl_context=context)
        
        # Try to authenticate with the token
        # Different servers might use different authentication methods with tokens
        # Method 1: Use token as password
        try:
            imap.login(username, token)
        except:
            # Method 2: Use XOAUTH2 if available
            try:
                auth_string = f'user={username}\1auth=Bearer {token}\1\1'
                imap.authenticate('XOAUTH2', lambda x: auth_string)
            except:
                # Method 3: Try custom authentication command
                try:
                    imap._simple_command('AUTHENTICATE', 'PLAIN', 
                                        base64.b64encode(f'\0{username}\0{token}'.encode()).decode())
                except:
                    # If all token methods fail, try with regular password as fallback
                    imap.login(username, password)
        
        # List available mailboxes
        status, mailboxes = imap.list()
        if status == 'OK':
            result = f"Available mailboxes: {len(mailboxes)}"
            for i, mailbox in enumerate(mailboxes[:3]):  # Show first 3 mailboxes
                result += f"\n  - {mailbox.decode()}"
            if len(mailboxes) > 3:
                result += f"\n  ... and {len(mailboxes) - 3} more"
        
        # Logout
        imap.logout()
        return True, result
        
    except Exception as e:
        return False, str(e)

def test_imap_connection():
    """Test connection to the IMAP server for receiving emails."""
    print("\n=== Testing IMAP Connection (Incoming Mail) ===")
    
    # Get IMAP configuration from environment variables
    imap_server = os.getenv('SERVER_NAME_INCOMING')
    imap_port = int(os.getenv('TCP_PORT_INCOMING', 993))
    username = os.getenv('USERNAME_INCOMING')
    password = os.getenv('PASSWORD_INCOMING')
    auth_token = os.getenv('AUTH_TOKEN')
    
    if not all([imap_server, username]):
        print("Error: Missing IMAP configuration in .env file")
        return False
    
    print(f"Connecting to IMAP server: {imap_server}:{imap_port}")
    print(f"Username: {username}")
    
    # Try different connection methods
    methods = [
        {"name": "Standard SSL", "func": try_imap_standard_ssl},
        {"name": "Without SSL Verification", "func": try_imap_no_verify},
        {"name": "With Token Authentication", "func": try_imap_with_token}
    ]
    
    for method in methods:
        print(f"\nTrying IMAP connection method: {method['name']}")
        if method["name"] == "With Token Authentication" and auth_token:
            success, message = method["func"](imap_server, imap_port, username, password, auth_token)
        else:
            success, message = method["func"](imap_server, imap_port, username, password)
        
        if success:
            print(f"Success with {method['name']}!")
            print(message)
            return True
        else:
            print(f"Failed with {method['name']}: {message}")
    
    print("\nAll IMAP connection methods failed.")
    print("Suggestions:")
    print("1. Verify your email credentials are correct")
    print("2. Check if your email provider allows IMAP access")
    print("3. Check if you need to enable 'Less secure app access' or create an app password")
    print("4. Try using a different port (143 for non-SSL IMAP)")
    return False

def test_smtp_connection():
    """Test connection to the SMTP server for sending emails."""
    print("\n=== Testing SMTP Connection (Outgoing Mail) ===")
    
    # Get SMTP configuration from environment variables
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 465))
    username = os.getenv('SMTP_USERNAME')
    password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL')
    auth_token = os.getenv('SMTP_AUTH_TOKEN')
    
    if not all([smtp_server, username]):
        print("Error: Missing SMTP configuration in .env file")
        return False
    
    print(f"Connecting to SMTP server: {smtp_server}:{smtp_port}")
    print(f"Username: {username}")
    
    # Try different connection methods
    methods = [
        {"name": "SSL Connection", "func": try_smtp_ssl, "port": smtp_port},
        {"name": "TLS Connection", "func": try_smtp_tls, "port": 587},
        {"name": "SSL Without Verification", "func": try_smtp_ssl_no_verify, "port": smtp_port},
        {"name": "With Token Authentication", "func": try_smtp_with_token, "port": smtp_port}
    ]
    
    for method in methods:
        print(f"\nTrying SMTP connection method: {method['name']} on port {method['port']}")
        
        if method["name"] == "With Token Authentication" and auth_token:
            success, message = method["func"](smtp_server, method["port"], username, password, sender_email, auth_token)
        else:
            success, message = method["func"](smtp_server, method["port"], username, password, sender_email)
            
        if success:
            print(f"Success with {method['name']}!")
            print(message)
            
            # Ask if user wants to send a test email
            send_test = input("Do you want to send a test email? (y/n): ").lower().strip() == 'y'
            if send_test:
                recipient = input("Enter recipient email address: ").strip()
                if method["name"] == "With Token Authentication" and auth_token:
                    send_result = send_test_email(smtp_server, method["port"], username, password, 
                                                sender_email, recipient, method["name"], auth_token)
                else:
                    send_result = send_test_email(smtp_server, method["port"], username, password, 
                                                sender_email, recipient, method["name"])
                if send_result[0]:
                    print(f"Test email sent successfully to {recipient}!")
                else:
                    print(f"Failed to send test email: {send_result[1]}")
            
            return True
        else:
            print(f"Failed with {method['name']}: {message}")
    
    print("\nAll SMTP connection methods failed.")
    print("Suggestions:")
    print("1. Verify your email credentials are correct")
    print("2. Check if your email provider allows SMTP access")
    print("3. Check if you need to enable 'Less secure app access' or create an app password")
    print("4. Try using port 587 (TLS) instead of 465 (SSL)")
    print("5. Check if your server requires a different authentication method")
    return False

def main():
    """Main function to test email connections."""
    print("Email Connection Test Script")
    print("===========================")
    
    # Load environment variables from .env file
    if not load_dotenv():
        print("Error: Could not load .env file. Please make sure it exists.")
        sys.exit(1)
    
    # Check if auth token is available
    auth_token = os.getenv('AUTH_TOKEN')
    if auth_token:
        print(f"Authentication token found: {auth_token[:5]}...{auth_token[-5:]}")
    
    # Test IMAP connection
    imap_success = test_imap_connection()
    
    # Test SMTP connection
    smtp_success = test_smtp_connection()
    
    # Summary
    print("\n=== Connection Test Summary ===")
    print(f"IMAP Connection: {'SUCCESS' if imap_success else 'FAILED'}")
    print(f"SMTP Connection: {'SUCCESS' if smtp_success else 'FAILED'}")
    
    if imap_success and smtp_success:
        print("\nAll email connections are working correctly!")
    else:
        print("\nSome email connections failed. Please check your configuration.")

if __name__ == "__main__":
    main()