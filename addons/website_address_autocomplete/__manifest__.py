# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Address Autocomplete',
    'category': 'Website/Website',
    'summary': 'Assist your users with automatic completion & suggestions when filling their address',
    'description': "Assist your users with automatic completion & suggestions when filling their address",
    'depends': [
        'website',
        'google_address_autocomplete',
    ],
    'data': [
        'views/templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'google_address_autocomplete/static/src/google_places_session.js',
            'website_address_autocomplete/static/src/interactions/address_form.js',
            'website_address_autocomplete/static/src/xml/autocomplete.xml',
        ],
        'web.assets_tests': [
            'website_address_autocomplete/static/tests/**/*.js'
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
