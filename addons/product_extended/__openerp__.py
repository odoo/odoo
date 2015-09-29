# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name" : "Product extension to track sales and purchases",
    "version" : "1.0",
    "author" : "OpenERP S.A.",
    "depends" : ["product", "purchase", "sale", "mrp", "stock_account"],
    "category" : "Generic Modules/Inventory Control",
    "description": """
Product extension. This module adds:
  * Computes standard price from the BoM of the product with a button on the product variant based
    on the materials in the BoM and the work centers.  It can create the necessary accounting entries when necessary.
""",
    "init_xml" : [],
    "demo_xml" : [],
    "data" : ["product_extended_wizard.xml","product_extended_view.xml","mrp_view.xml", 'security/ir.model.access.csv'],
    "active": False,
    "installable": True
}
