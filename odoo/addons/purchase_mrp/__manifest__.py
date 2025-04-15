# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Purchase and MRP Management',
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'description': """
This module provides facility to the user to install mrp and purchase modules at a time.
========================================================================================

It is basically used when we want to keep track of production orders generated
from purchase order.
    """,
    'data': [
        'views/mrp_bom_views.xml',
        'views/purchase_order_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_orderpoint_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/purchase_mrp_demo.xml',
    ],
    'depends': ['mrp', 'purchase_stock'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'mrp/static/src/**/*.js',
        ],
    },
    'license': 'LGPL-3',
}
