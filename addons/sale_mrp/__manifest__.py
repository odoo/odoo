{
    "name": "Sales and MRP Management",
    "version": "1.1",
    "category": "Sales/Sales",
    "description": """
This module provides facility to the user to install mrp and sales modules at a time.
====================================================================================

It is basically used when we want to keep track of production orders generated
from sales order. It adds sales name and sales Reference on production order.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mrp",
        "sale_stock",
    ],
    "data": [
        "security/ir.access.csv",
        "views/mrp_production_views.xml",
        "views/sale_order_views.xml",
        "views/sale_portal_templates.xml",
    ],
    "auto_install": True,
}
