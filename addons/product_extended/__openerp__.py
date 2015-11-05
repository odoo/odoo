# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Product extension to track sales and purchases",
    "author" : "Odoo S.A.",
    "depends" : ["product", "purchase", "sale", "mrp"],
    "category" : "Generic Modules/Inventory Control",
    "description": """
Product extension. This module adds:
  * Computes standard price from the BoM of the product with a button on the product variant based
    on the materials in the BoM and the work centers.  It can create the necessary accounting entries when necessary.
""",
    "init_xml" : [],
    "demo_xml" : [],
    "data" : [
        'security/ir.model.access.csv',
        'wizard/wizard_price_views.xml',
        'views/mrp_views.xml',
        'views/product_views.xml',
    ],
}
