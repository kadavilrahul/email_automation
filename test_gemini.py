import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API')

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"

data = {
    "contents": [{
        "parts": [{
            "text": "What is the capital of France?"
        }]
    }]
}

try:
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
    print(result)
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
