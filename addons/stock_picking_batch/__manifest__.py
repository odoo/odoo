# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Warehouse Management: Batch Transfer',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'description': """
This module adds the batch transfer option in warehouse management
==================================================================
    """,
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_batch_views.xml',
        'views/stock_picking_wave_views.xml',
        'views/stock_move_line_views.xml',
        'data/stock_picking_batch_data.xml',
        'wizard/stock_picking_to_batch_views.xml',
        'wizard/stock_add_to_wave_views.xml',
        'report/stock_picking_batch_report_views.xml',
        'report/report_picking_batch.xml',
    ],
    'demo': [
        'data/stock_picking_batch_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_picking_batch/static/src/js/*',
        ]
    },
    'installable': True,
    'license': 'LGPL-3',
}
