# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Worldline",
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A French payment provider covering several European countries.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_worldline_templates.xml',

        'data/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
