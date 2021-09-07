# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Time Off',
    'version': '1.0',
    'icon': '/l10n_fr/static/description/icon.png',
    'summary': 'Management of leaves for part-time workers in France',
    'depends': ['hr_holidays'],
    'auto_install': False,
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}
