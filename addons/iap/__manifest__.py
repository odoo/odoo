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
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/iap_views.xml',
        'views/res_config_settings.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'iap/static/src/js/**/*',
        ],
        'web.tests_assets': [
            'iap/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'iap/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
