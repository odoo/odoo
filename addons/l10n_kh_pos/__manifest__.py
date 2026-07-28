# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Cambodia - Point of Sale',
    'countries': ['kh'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Point of Sale',
    'summary': """Khmer localization for Point of Sale""",
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'l10n_kh',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_kh_pos/static/src/**/*',
        ],
    },
    'data': [
        "views/res_config_settings_views.xml"
    ],
}
