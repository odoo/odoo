# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gulf Cooperation Council - Point of Sale',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
Adds Arabic as a secondary language on your receipt
    """,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'l10n_gcc_invoice'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_gcc_pos/static/src/**/*',
        ]
    },
    'auto_install': True,
}
