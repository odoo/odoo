# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Warehouse Management: Waves',
    'version': '1.0',
    'category': 'Warehouse',
    'description': """
This module adds the picking wave option in warehouse management
================================================================
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_wave_views.xml',
        'data/stock_picking_wave_data.xml',
        'wizard/stock_picking_to_wave_views.xml',
    ],
    'demo': [
        'data/stock_picking_wave_demo.xml',
    ],
    'installable': True,
}
