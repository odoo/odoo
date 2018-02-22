# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Product Extension: Compute price from BoM",
    "version" : "1.0",
    "depends" : ["mrp", "stock_account"],
    "category" : "Manufacturing",
    "description": """
Allows to compute the standard price of the product based on its BoM,
using the prices of its components and the cost linked to the work centers.
It adds a button on the product itself but also an action in the list view of the products.
If the automated inventory valuation is active, the required accounting entries will be created.
""",
    "init_xml" : [],
    "demo_xml" : [],
    "data": ["views/product_views.xml"],
    "active": False,
    "installable": True
}
