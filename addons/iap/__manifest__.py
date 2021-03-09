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
            # inside .
            'iap/static/src/js/iap_credit.js',
            # inside .
            'iap/static/src/js/crash_manager.js',
            # inside .
            'iap/static/src/js/iap_buy_more_credits.js',
        ],
        'web.tests_assets': [
            # inside .
            'iap/static/tests/helpers/mock_server.js',
        ],
        'web.assets_qweb': [
            'iap/static/src/xml/iap_templates.xml',
        ],
    }
}
