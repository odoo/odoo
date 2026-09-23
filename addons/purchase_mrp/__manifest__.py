{
    "name": "Purchase and MRP Management",
    "version": "1.1",
    "category": "Supply Chain/Purchase",
    "description": """
This module provides facility to the user to install mrp and purchase modules at a time.
========================================================================================

It is basically used when we want to keep track of production orders generated
from purchase order.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mrp",
        "purchase_stock",
    ],
    "data": [
        "views/mrp_bom_views.xml",
        "views/purchase_order_views.xml",
        "views/mrp_production_views.xml",
        "views/stock_orderpoint_views.xml",
        "security/ir.access.csv",
    ],
    "demo": [
        "demo/purchase_mrp_demo.xml",
    ],
    "auto_install": True,
}
