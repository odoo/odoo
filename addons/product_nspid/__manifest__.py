# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Products NS-PID",
    "version": "1.0",
    "category": "Inventory",
    "depends": ["product"],
    "description": """
        This module adds the Manufacturing PID to the product inventory page. Starting from 1 november 2026, this NS-PID
        is required when importing packages into the EU.
    """,
    "data": [
        "views/product_views.xml",
    ],
    "auto_install": True,
    "license": "LGPL-3",
}
