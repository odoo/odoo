# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United Arab Emirates - Point of Sale',
    'countries': ['ae'],
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
United Arab Emirates POS Localization
===========================================================
    """,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'depends': [
        'l10n_gcc_pos',
        'l10n_ae',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_ae_pos/static/src/**/*',
        ]
    },
    'auto_install': True,
}
