# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Point of Sale',
    'version': '1.0',
    'countries': ['pt'],
    'description': """Point of Sale module for Portugal which allows hash and QR code on POS orders""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'point_of_sale',
        'l10n_pt_account',
    ],
    'auto_install': [
        'point_of_sale',
        'l10n_pt_account',
    ],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'report/l10n_pt_pos_hash_integrity_templates.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_pt_pos/static/src/js/**/*',
            'l10n_pt_pos/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
