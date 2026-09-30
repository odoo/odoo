# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Google Address Autocomplete",
    'summary': 'Assist with automatic completion & suggestions when filling address',
    'version': '1.0',
    'description': """
This module Auto complete the address data.
    """,
    'category': 'Hidden/Tools',
    'depends': ['web'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'google_address_autocomplete/static/src/**/*',
            ('remove', "google_address_autocomplete/static/src/address_autocomplete/google_address_autocomplete_dark.scss"),
        ],
        "web.assets_web_dark": [
            "google_address_autocomplete/static/src/address_autocomplete/google_address_autocomplete_dark.scss",
        ],
        'web._assets_core': [
            'google_address_autocomplete/static/src/address_autocomplete/google_address_autocomplete.scss',
        ],
        'web.assets_tests': [
            'google_address_autocomplete/static/tests/tours/*.js'
        ],
        'web.assets_unit_tests': [
            'google_address_autocomplete/static/tests/**/*.test.js',
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
