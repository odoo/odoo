# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Point of Sale',
    'countries': ['in'],
    'version': '1.0',
    'description': """GST Point of Sale""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_in',
        'point_of_sale'
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_in_pos/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
