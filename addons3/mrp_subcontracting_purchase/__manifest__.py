# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase and Subcontracting Management',
    'version': '0.1',
    'category': 'Manufacturing/Purchase',
    'description': """
This bridge module adds some smart buttons between Purchase and Subcontracting
    """,
    'depends': ['mrp_subcontracting', 'purchase_mrp'],
    'data': [
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'demo': [
        'data/mrp_subcontracting_purchase_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
