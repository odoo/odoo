{
    "name": "POS Purchase",
    "category": "Sales/Point of Sale",
    'author': 'Odoo S.A.',
    "summary": "PoS Order/Purchase Order relation",
    "description": """
Bridge between the POS, Inventory and Purchase modules.
""",
    "depends": ["pos_stock", "purchase_stock"],
    "data": [
        "views/pos_order_views.xml",
    ],
    "auto_install": True,
    "license": "LGPL-3",
}
