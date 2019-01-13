# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Product Extension: Compute cost from BoM",
    "version" : "1.0",
    "depends" : ["mrp", "stock_account"],
    "category" : "Manufacturing",
    "description": """
Allows to compute the cost of the product based on its BoM,
using the costs of its components and work center operations.
It adds a button on the product itself but also an action in the list view of the products.
If the automated inventory valuation is active, the necessary accounting entries will be created.
""",
    "init_xml" : [],
    "demo_xml" : [],
    "data": ["views/product_views.xml"],
    "active": False,
    "installable": True
}
