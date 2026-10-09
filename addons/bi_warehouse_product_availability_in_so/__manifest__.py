# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name":"Warehouse Product Availability in SO",
    "version":"16.0.0.2",
    "category":"Warehouse",
    "summary":"warehouse sale order line product available availability warehouse product stock available availability warehouse location wise product availability warehouse sale order product quantity sale product availability warehouse product available quantity",
    "description":"""
    		 
        Warehouse Product Quantity in SO Odoo App helps users to show product availability in sales order with location detailed quantity in warehouse. User can easily view product available quantity with detailed location as per warehouse wise in the sales order line.

    """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.com',
    "depends":["base",
               "sale_management",
               "sale",
               "stock",
	          ],
    "data":[
            "security/ir.model.access.csv",
            "wizard/available_quantities_wizard_view.xml",
            "views/sale_order_view.xml",
	       ],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/hJ591hfK7K4',
    "images":['static/description/Warehouse-Product-Availability-SO-Banner.gif'],
}
