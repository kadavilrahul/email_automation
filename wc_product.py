from agno.agent import Agent
from agno.models.google.gemini import Gemini
import os
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

load_dotenv()

# Get API keys from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Check if all required environment variables are set
if not GEMINI_API_KEY:
    raise ValueError("Missing required environment variables")

wc_url = os.getenv('WC_URL')
wc_key = os.getenv('WC_KEY')
wc_secret = os.getenv('WC_SECRET')

def search_products(query: str, category: str = None) -> str:
    """Tool to search products using the WooCommerce API"""
    try:
        auth = (wc_key, wc_secret)
        params = {'search': query}
        if category:
            params['category'] = category

        response = requests.get(
            f"{wc_url}/wp-json/wc/v3/products",
            auth=HTTPBasicAuth(*auth),
            params=params
        )
        response.raise_for_status()
        products = response.json()

        if not products:
            return f"No products found matching '{query}'"

        result = []
        for product in products[:5]:  # Limit to first 5 products
            result.append(
                f"- {product['name']}\n"
                f"  Price: Rs.{product['price']}"
            )

        return "Found products:\n" + "\n".join(result)
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

search_products.__name__ = "ProductSearchTool"
search_products.description = "Search for products in the WooCommerce store"
search_products.parameters = {
    "query": {"type": "string", "description": "Search term for products"},
    "category": {"type": "string", "description": "Optional category to filter products", "optional": True}
}

def get_categories() -> str:
    """Tool to get all product categories"""
    try:
        auth = (wc_key, wc_secret)
        response = requests.get(
            f"{wc_url}/wp-json/wc/v3/products/categories",
            auth=HTTPBasicAuth(*auth)
        )
        response.raise_for_status()
        categories = response.json()

        if not categories:
            return "No categories found"

        result = ["Available categories:"]
        for category in categories:
            result.append(f"- {category['name']} (ID: {category['id']})")

        return "\n".join(result)
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

get_categories.__name__ = "CategoryListTool"
get_categories.description = "Get all product categories"
get_categories.parameters = {}

# Create the Product Search Agent
agent = Agent(
    model=Gemini(
        id="gemini-2.0-flash-exp",
        api_key=GEMINI_API_KEY,
        generative_model_kwargs={},
        generation_config={}
    ),
    tools=[search_products, get_categories],
    instructions="Search for products in the WooCommerce store. You can search by keyword and optionally filter by category.",
    show_tool_calls=True,
    markdown=True,
)

def display_menu():
    """Display the main menu options"""
    print("\n=== Product Search Menu ===")
    print("1. Search Products")
    print("2. List Categories")
    print("3. Search Products by Category")
    print("4. Exit")
    return input("Enter your choice (1-4): ")

def run_product_search():
    """Run product search"""
    query = input("\nEnter search term: ")
    response = search_products(query)
    print("\nSearch Results:")
    print(response)

def run_category_list():
    """List all categories"""
    response = get_categories()
    print("\nCategory List:")
    print(response)

def run_category_search():
    """Search products in a specific category"""
    print("\nFirst, let's see available categories:")
    categories = get_categories()
    print(categories)
    
    category = input("\nEnter category ID: ")
    query = input("Enter search term: ")
    response = search_products(query, category)
    print("\nSearch Results:")
    print(response)

def main():
    while True:
        choice = display_menu()
        
        if choice == '1':
            run_product_search()
        elif choice == '2':
            run_category_list()
        elif choice == '3':
            run_category_search()
        elif choice == '4':
            print("\nExiting program...")
            break
        else:
            print("\nInvalid choice. Please select a number between 1 and 4.")

if __name__ == "__main__":
    main()