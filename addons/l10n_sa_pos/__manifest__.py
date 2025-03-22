# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi Arabia - Point of Sale',
    'countries': ['sa'],
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
Saudi Arabia POS Localization
===========================================================
    """,
    'license': 'LGPL-3',
    'depends': [
        'l10n_gcc_pos',
        'l10n_sa',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'web/static/lib/zxing-library/zxing-library.js',
            'l10n_sa_pos/static/src/**/*',
        ]
    },
    'auto_install': True,
}
