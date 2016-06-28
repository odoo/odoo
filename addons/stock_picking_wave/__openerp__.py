# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Warehouse Management: Waves',
    'version': '1.0',
    'category': 'Stock Management',
    'description': """
This module adds the picking wave option in warehouse management.
=================================================================
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['stock'],
    'data': ['security/ir.model.access.csv',
            'views/stock_picking_wave_views.xml',
            'data/stock_picking_wave_data.xml',
            'data/ir_sequence_data_picking_wave.xml',
            'wizard/stock_picking_to_wave_views.xml',
            ],
    'demo': [
            'data/stock_picking_wave_demo.xml',
             ],
    'installable': True,
}
