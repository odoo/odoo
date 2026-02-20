#!/usr/bin/env python3
"""
Uber Eats Test Order Generator
Usage: python3 uber_test_orders.py [--product-id ID] [--quantity N] [--customer-name NAME]
"""

import json
import hmac
import hashlib
import psycopg2
import argparse
import random
from urllib.request import Request, urlopen
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'odoo_db',
    'database': 'ram-db',
    'user': 'odoo',
    'password': 'Postgres_911'
}

# Sample customer data for variation
SAMPLE_CUSTOMERS = [
    {"first_name": "Rajesh", "last_name": "Kumar", "phone": "+919876543210"},
    {"first_name": "Priya", "last_name": "Sharma", "phone": "+919876543211"},
    {"first_name": "Amit", "last_name": "Patel", "phone": "+919876543212"},
    {"first_name": "Neha", "last_name": "Singh", "phone": "+919876543213"},
    {"first_name": "Vikram", "last_name": "Reddy", "phone": "+919876543214"},
]

SAMPLE_ADDRESSES = [
    {"street": "123 MG Road", "city": "Delhi", "state": "Delhi", "zip": "110001"},
    {"street": "45 Connaught Place", "city": "New Delhi", "state": "Delhi", "zip": "110002"},
    {"street": "78 Nehru Place", "city": "Delhi", "state": "Delhi", "zip": "110019"},
    {"street": "12 Saket", "city": "Delhi", "state": "Delhi", "zip": "110017"},
    {"street": "90 Lajpat Nagar", "city": "Delhi", "state": "Delhi", "zip": "110024"},
]

SPECIAL_INSTRUCTIONS = [
    "Extra spicy please",
    "No onions",
    "Pack separately",
    "Add extra sauce",
    "Contactless delivery",
]


def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG)


def get_client_secret():
    """Get Uber client secret from database"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT client_secret FROM pos_aggregator_config WHERE provider = 'ubereats' LIMIT 1")
    secret = cur.fetchone()[0]
    conn.close()
    return secret


def get_available_products():
    """Get products with uber_eats_id mapping"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT pp.id, pt.name->>'en_US' as name, pp.uber_eats_id, pt.list_price
        FROM product_product pp
        JOIN product_template pt ON pp.product_tmpl_id = pt.id
        WHERE pp.uber_eats_id IS NOT NULL
        AND pt.active = true
        AND pt.available_in_pos = true
    """)
    products = cur.fetchall()
    conn.close()
    return products


def create_order_payload(product_id=None, quantity=1, customer=None, address=None, instructions=None):
    """Create Uber order payload"""
    
    # Get product info
    conn = get_db_connection()
    cur = conn.cursor()
    
    if product_id:
        cur.execute("""
            SELECT pp.id, pt.name->>'en_US', pp.uber_eats_id, pt.list_price
            FROM product_product pp
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE pp.id = %s
        """, (product_id,))
        product = cur.fetchone()
        
        if not product or not product[2]:
            print(f"❌ Product {product_id} not found or has no uber_eats_id")
            conn.close()
            return None
    else:
        # Get random product with uber_eats_id
        cur.execute("""
            SELECT pp.id, pt.name->>'en_US', pp.uber_eats_id, pt.list_price
            FROM product_product pp
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE pp.uber_eats_id IS NOT NULL
            AND pt.active = true
            AND pt.available_in_pos = true
            LIMIT 1
        """)
        product = cur.fetchone()
    
    conn.close()
    
    if not product:
        print("❌ No products with uber_eats_id found")
        return None
    
    prod_id, prod_name, uber_id, price = product
    
    # Use provided or random data
    customer = customer or random.choice(SAMPLE_CUSTOMERS)
    address = address or random.choice(SAMPLE_ADDRESSES)
    instructions = instructions or random.choice(SPECIAL_INSTRUCTIONS)
    
    # Generate unique order ID
    timestamp = int(datetime.now().timestamp())
    order_id = f"uber-order-{timestamp}"
    
    # Calculate total (convert price to cents)
    unit_price_cents = int(price * 100)
    total_cents = unit_price_cents * quantity
    
    # Create payload
    payload = {
        "id": order_id,
        "uuid": f"uuid-{timestamp}",
        "total_price": total_cents,
        "total": total_cents,
        "cart": {
            "items": [{
                "id": f"item-{timestamp}",
                "external_id": uber_id,
                "quantity": quantity,
                "price": unit_price_cents,
                "title": prod_name
            }]
        },
        "eater": {
            "first_name": customer["first_name"],
            "last_name": customer["last_name"],
            "phone": customer["phone"]
        },
        "delivery_address": {
            "address_line": address["street"],
            "city": address["city"],
            "state": address["state"],
            "zip": address["zip"]
        },
        "special_instructions": instructions
    }
    
    return payload, prod_name, price


def send_order(payload):
    """Send order to webhook with signature"""
    
    client_secret = get_client_secret()
    
    # Convert to JSON
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate signature
    signature = hmac.new(
        client_secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Send request
    req = Request(
        'http://localhost:8069/api/delivery/uber',
        payload_bytes,
        {
            'Content-Type': 'application/json',
            'X-Uber-Signature': signature
        },
        method='POST'
    )
    
    response = urlopen(req)
    return json.loads(response.read().decode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description='Generate Uber Eats test orders')
    parser.add_argument('--product-id', type=int, help='Product ID (leave empty for random)')
    parser.add_argument('--quantity', type=int, default=1, help='Quantity (default: 1)')
    parser.add_argument('--customer-name', help='Customer name (e.g., "John Doe")')
    parser.add_argument('--phone', help='Customer phone')
    parser.add_argument('--count', type=int, default=1, help='Number of orders to create')
    parser.add_argument('--list-products', action='store_true', help='List available products')
    
    args = parser.parse_args()
    
    # List products if requested
    if args.list_products:
        print("\n=== AVAILABLE PRODUCTS ===\n")
        products = get_available_products()
        for prod in products:
            print(f"ID: {prod[0]:3d} | Name: {prod[1]:30s} | Uber ID: {prod[2]:30s} | Price: ₹{prod[3]:.2f}")
        print(f"\nTotal: {len(products)} products\n")
        return
    
    # Prepare customer data if provided
    customer = None
    if args.customer_name or args.phone:
        names = args.customer_name.split() if args.customer_name else ["Test", "Customer"]
        customer = {
            "first_name": names[0],
            "last_name": names[1] if len(names) > 1 else "",
            "phone": args.phone or "+919876543210"
        }
    
    # Create orders
    print(f"\n{'=' * 60}")
    print(f"Creating {args.count} test order(s)...")
    print(f"{'=' * 60}\n")
    
    success_count = 0
    for i in range(args.count):
        try:
            # Create payload
            result = create_order_payload(
                product_id=args.product_id,
                quantity=args.quantity,
                customer=customer
            )
            
            if not result:
                continue
            
            payload, prod_name, price = result
            
            # Send order
            response = send_order(payload)
            
            print(f"✅ Order {i+1}/{args.count} created successfully!")
            print(f"   Product: {prod_name}")
            print(f"   Quantity: {args.quantity}")
            print(f"   Total: ₹{price * args.quantity:.2f}")
            print(f"   Customer: {payload['eater']['first_name']} {payload['eater']['last_name']}")
            print(f"   POS Reference: {response.get('pos_ref', 'N/A')}")
            print(f"   Order ID: {response.get('order_id', 'N/A')}")
            print()
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ Order {i+1}/{args.count} failed: {str(e)}\n")
    
    print(f"{'=' * 60}")
    print(f"Summary: {success_count}/{args.count} orders created successfully")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
