# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Iyzico",
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider covering Turkey.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_iyzico_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',  # Depends on views/payment_iyzico_templates.xml
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
