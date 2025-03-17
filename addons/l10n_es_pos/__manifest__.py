# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Spain - Point of Sale',
    'category': 'Accounting/Localizations/Point of Sale',
    'summary': """Spanish localization for Point of Sale""",
    'depends': ['point_of_sale', 'l10n_es'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_es_pos/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_es_pos/static/tests/**/*',
        ],
    },
}
