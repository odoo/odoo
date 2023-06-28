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
        'l10n_pt',
    ],
    'installable': True,
    'auto_install': [
        'point_of_sale',
        'l10n_pt',
    ],
    'license': 'LGPL-3',
}
