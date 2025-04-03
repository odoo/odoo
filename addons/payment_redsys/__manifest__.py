# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Redsys',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "Spanish payment provider",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'data/payment_provider_data.xml',

    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
