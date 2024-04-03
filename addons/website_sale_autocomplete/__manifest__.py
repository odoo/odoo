# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google places autocompletion',
    'category': 'Website/Website',
    'summary': 'Assist your users with automatic completion & suggestions when filling their address during checkout',
    'version': '1.0',
    'description': "Assist your users with automatic completion & suggestions when filling their address during checkout",
    'depends': [
        'website_sale'
    ],
    'data': [
        'views/templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_autocomplete/static/src/js/address_form.js',
            'website_sale_autocomplete/static/src/xml/autocomplete.xml',
        ],
        'web.assets_tests': [
            'website_sale_autocomplete/static/tests/**/*.js'
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
