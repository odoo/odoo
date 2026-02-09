import requests
import json
import sys

BASE_URL = "http://localhost:8069"

def test_product_details(product_id):
    print(f"\n--- Testing Product Details (ID: {product_id}) ---")
    payload = {
        "params": {
            "product_id": product_id
        }
    }
    response = requests.post(f"{BASE_URL}/ram/product/details", json=payload)
    if response.status_code == 200:
        result = response.json().get('result', {})
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Success! Fetched: {result['name']}")
            print(f"Attributes: {len(result.get('attributes', []))}")
            print(f"Combos: {len(result.get('combos', []))}")
            return result
    else:
        print(f"Failed with status: {response.status_code}")
    return None

def test_order_submission(details):
    print("\n--- Testing Complex Order Submission ---")
    
    # Construct a complex order line
    line = {
        "product_id": details['id'],
        "qty": 1,
        "price": details['list_price'],
        "name": details['name'],
        "attribute_value_ids": [],
        "combo_line_ids": []
    }
    
    # Add first attribute value if available
    if details.get('attributes'):
        line['attribute_value_ids'] = [details['attributes'][0]['values'][0]['id']]
        print(f"Selected Attribute: {details['attributes'][0]['values'][0]['name']}")

    # Add first combo item if available
    if details.get('combos'):
        combo = details['combos'][0]
        item = combo['items'][0]
        line['combo_line_ids'] = [{
            "combo_id": combo['id'],
            "combo_item_id": item['id'],
            "product_id": item['product_id'],
            "qty": 1
        }]
        print(f"Selected Combo Item: {item['name']}")

    order_data = {
        "customer_name": "Test User",
        "customer_phone": "9876543210",
        "delivery_address": "123 Verification St",
        "lines": [line]
    }
    
    payload = {
        "params": {
            "order_data": order_data
        }
    }
    
    # We need a CSRF session for this. Simplest way for script is to fetch a page first.
    session = requests.Session()
    session.get(f"{BASE_URL}/ram/menu") # Get session cookie
    
    response = session.post(f"{BASE_URL}/ram/order/submit", json=payload)
    if response.status_code == 200:
        result = response.json().get('result', {})
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Success! Order Ref: {result['pos_reference']}")
            print(f"Status: {result['status']}")
    else:
        print(f"Failed with status: {response.status_code}")

if __name__ == "__main__":
    # 1. Find a product that is available in POS to test
    # (Assuming ID 1 exists and is a POS product from previous scripts)
    # The user might have specific ones, but we'll try to fetch one from the menu logic if needed.
    
    # For now, let's try a common ID or ask the user to provide one.
    # Since I don't want to block, I'll try to find one via shell first or just use a known one.
    # I'll use a product ID I saw earlier or just try 1.
    details = test_product_details(1)
    if details:
        test_order_submission(details)
    else:
        print("Could not find test product. Please ensure a product with ID 1 is 'Available in POS'.")
