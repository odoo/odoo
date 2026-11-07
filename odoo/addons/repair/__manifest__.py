# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Repairs',
    'version': '1.0',
    'sequence': 230,
    'category': 'Inventory/Inventory',
    'summary': 'Repair damaged products',
    'description': """
The aim is to have a complete module to manage all products repairs.
====================================================================

The following topics are covered by this module:
------------------------------------------------------
    * Add/remove products in the reparation
    * Impact for stocks
    * Warranty concept
    * Repair quotation report
    * Notes for the technician and for the final customer
""",
    'depends': ['stock', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/repair_security.xml',
        'wizard/stock_warn_insufficient_qty_views.xml',
        'wizard/repair_warn_uncomplete_move.xml',
        'views/product_views.xml',
        'views/stock_move_views.xml',
        'views/repair_views.xml',
        'views/sale_order_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse_views.xml',
        'report/repair_reports.xml',
        'report/repair_templates_repair_order.xml',
        'data/repair_data.xml',
    ],
    'demo': ['data/repair_demo.xml'],
    'post_init_hook': '_create_warehouse_data',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
