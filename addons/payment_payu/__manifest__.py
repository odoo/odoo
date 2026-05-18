# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: PayU",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider covering India.",
    'description': " ",  # Non-empty string to avoid loading the README file.,
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_payu_templates.xml',

        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_payu/static/src/interactions/payment_form.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'author': "Odoo S.A.",
    'license': 'LGPL-3',
}
