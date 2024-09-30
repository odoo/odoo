# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Address Autocomplete",
    'summary': 'Assist with automatic completion & suggestions when filling address',
    'version': '1.0',
    'description': """
This module Auto complete the address data.
    """,
    'category': 'Hidden/Tools',
    'depends': ['base_setup'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'address_autocomplete/static/src/xml/extended_autocomplete_template.xml',
            'address_autocomplete/static/src/js/extended_autocomplete.js',
            'address_autocomplete/static/src/xml/address_autocomplete_template.xml',
            'address_autocomplete/static/src/js/address_autocomplete.js',
        ],
        'web._assets_core': [
            'address_autocomplete/static/src/scss/address_autocomplete.scss',
        ],
        'web.assets_tests': [
            'address_autocomplete/static/tests/**/*.js'
        ],
    },
    'license': 'LGPL-3',
}
