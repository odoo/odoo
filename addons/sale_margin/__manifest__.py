{
    "name": "Margins in Sales Orders",
    "version": "1.0",
    "category": "Sales/Sales",
    "description": """
This module adds the 'Margin' on sales order.
=============================================

This gives the profitability by calculating the difference between the Unit
Price and Cost Price.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "sale",
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "demo": [
        "demo/sale_margin_demo.xml",
    ],
}
