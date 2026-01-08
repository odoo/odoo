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
        'views/stock_picking_type_views.xml',
        'views/stock_picking_wave_views.xml',
        'views/stock_move_line_views.xml',
        'views/stock_picking_views.xml',
        'data/stock_picking_batch_data.xml',
        'wizard/stock_picking_to_batch_views.xml',
        'wizard/stock_add_to_wave_views.xml',
        'report/stock_picking_batch_report_views.xml',
        'report/report_picking_batch.xml',
        'security/stock_picking_batch_security.xml',
    ],
    'demo': [
        'data/stock_picking_batch_demo.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_tests': [
            'stock_picking_batch/static/tests/tours/**/*',
        ],
    },
}
