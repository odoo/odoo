# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Mollie',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A Dutch payment provider covering several European countries.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'author': 'Odoo S.A, Applix BV, Droggol Infotech Pvt. Ltd.',
    'website': 'https://www.mollie.com',
    'depends': ['payment'],
    'data': [
        'views/payment_mollie_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',
    ],
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
