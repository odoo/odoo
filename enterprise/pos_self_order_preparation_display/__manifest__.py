# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'pos self prep display',
    'version': '1.0.0',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'depends': ['pos_self_order', 'pos_preparation_display'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'pos_preparation_display.assets': [
            'pos_self_order_preparation_display/static/src/override/pos_preparation_display/**/*',
        ],
    },
    'license': 'OEEL-1',
}
