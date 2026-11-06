# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name": "Warehouse Product availability in PO",
    "version": "16.0.0.1",
    "category": "Warehouse",
    "summary": "warehouse purchase order line product available quantity warehouse product stock available quantity warehouse location wise product quantity warehouse purchase order product quantity purchase product available quantity warehouse product available  quantity",
    "description": """

        This Odoo App helps users to show product availability in purchase order with location detailed quantity in warehouse. User can easily view product available quantity with detailed location as per warehouse wise in the purchase order line.

	""",
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.com',
    "depends": ["base",
                "crm",
                "sale",
                "account",
                "purchase",
                "sale_management",
                "stock",
                ],
    "data": [
           "security/ir.model.access.csv",
           "wizard/product_available_quantity_wizard_view.xml",
           "views/purchase_order_view.xml",

        ],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/_nRacKbpt-Y',
    "images":['static/description/Warehouse-Product-Quantity-Purchase-Order-Banner.gif'],
}


