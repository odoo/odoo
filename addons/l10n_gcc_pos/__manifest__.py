# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gulf Cooperation Council - Point of Sale',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
GCC POS Localization
=======================================================
    """,
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'l10n_gcc_invoice'],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_gcc_pos/static/src/**/*',
        ]
    },
    'auto_install': True,
}
