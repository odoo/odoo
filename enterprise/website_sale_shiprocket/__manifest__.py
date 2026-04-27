{
    'name': 'Shiprocket: Cash on Delivery',
    'category': 'Inventory/Delivery',
    'summary': 'Provide cash on delivery for website users',
    'description': """
This module allows ecommerce users to book an order with the shiprocket using cash on delivery feature.
    """,
    'depends': ['delivery_shiprocket', 'website_sale', 'payment_custom'],
    'data': [
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on `shiprocket_payment_method_cash_on_delivery`.
        'views/delivery_shiprocket_templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'auto_install': ['delivery_shiprocket', 'website_sale'],
    'license': 'OEEL-1',
}
