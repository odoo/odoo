# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Product extension to track sales and purchases",
    "version" : "1.0",
    "depends" : ["mrp", "stock_account"],
    "category" : "Manufacturing",
    "description": """
Product extension. This module adds:
  * Computes standard price from the BoM of the product with a button on the product variant based
    on the materials in the BoM and the work centers.  It can create the necessary accounting entries when necessary.
""",
    "init_xml" : [],
    "demo_xml" : [],
    "data": ["views/product_views.xml"],
    "active": False,
    "installable": True
}
