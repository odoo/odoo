# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Warehouse Management: Batch Picking',
    'version': '1.0',
    'category': 'Warehouse',
    'description': """
This module adds the batch picking option in warehouse management
=================================================================
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_batch_views.xml',
        'data/stock_picking_batch_data.xml',
        'wizard/stock_picking_to_batch_views.xml',
    ],
    'demo': [
        'data/stock_picking_batch_demo.xml',
    ],
    'installable': True,
}
