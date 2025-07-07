# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'In-App Purchases',
    'category': 'Hidden/Tools',
    'version': '1.1',
    'summary': 'Basic models and helpers to support In-App purchases.',
    'description': """
This module provides standard tools (account model, context manager and helpers)
to support In-App purchases inside Odoo. """,
    'depends': [
        'web',
        'base_setup'
    ],
    'data': [
        'data/services.xml',
        'views/iap_views.xml',
        'views/res_config_settings.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'iap/static/src/**/*.js',
            'iap/static/src/**/*.xml',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
