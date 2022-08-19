# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Colombian - Point of Sale',
    'icon': '/l10n_co/static/description/icon.png',
    'version': '1.0',
    'description': """Colombian - Point of Sale""",
    'category': 'Accounting/Localizations/Point of Sale',
    'auto_install': True,
    'depends': [
        'l10n_co',
        'point_of_sale'
    ],
    'data': [
        'views/res_config_settings_views.xml'
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_co_pos/static/src/js/**/*',
            'l10n_co_pos/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
