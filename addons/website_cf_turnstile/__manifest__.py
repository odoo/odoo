# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Cloudflare Turnstile',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
This module implements Cloudflare Turnstile so that you can prevent bot spam on your forms.
    """,
    'depends': ['website'],
    'data': [
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_cf_turnstile/static/src/interactions/**/*.js',
        ],
        'web.assets_unit_tests': [
            'website_cf_turnstile/static/tests/interactions/**/*',
        ],
        'web.assets_unit_tests_setup': [
            'website_cf_turnstile/static/src/interactions/**/*.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
}
