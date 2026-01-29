# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Authorize.Net',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "An payment provider covering the US, Australia, and Canada.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_authorize_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_token_views.xml',

        'data/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_authorize/static/src/scss/payment_authorize.scss',
            'payment_authorize/static/src/js/payment_form.js',
        ],
    },
    'license': 'LGPL-3',
}
