# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Google Address Autocomplete",
    'summary': 'Assist with automatic completion & suggestions when filling address',
    'version': '1.0',
    'description': """
This module Auto complete the address data.
    """,
    'category': 'Hidden/Tools',
    'depends': ['base_setup'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'google_address_autocomplete/static/src/xml/extended_autocomplete_template.xml',
            'google_address_autocomplete/static/src/js/extended_autocomplete.js',
            'google_address_autocomplete/static/src/xml/google_address_autocomplete_template.xml',
            'google_address_autocomplete/static/src/js/google_address_autocomplete.js',
        ],
        'web._assets_core': [
            'google_address_autocomplete/static/src/scss/google_address_autocomplete.scss',
        ],
        'web.assets_tests': [
            'google_address_autocomplete/static/tests/**/*.js'
        ],
    },
    'license': 'LGPL-3',
}
