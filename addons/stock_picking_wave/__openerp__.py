# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Warehouse Management: Waves',
    'version': '1.0',
    'category': 'Warehouse',
    'description': """
This module adds the picking wave option in warehouse management.
=================================================================
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['stock'],
    'data': ['security/ir.model.access.csv',
            'stock_picking_wave_view.xml',
            'stock_picking_wave_data.xml',
            'stock_picking_wave_sequence.xml',
            'wizard/picking_to_wave_view.xml',
            ],
    'demo': [
            'stock_picking_wave_demo.xml',
             ],
    'installable': True,
    'auto_install': False,
}
