# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Paypal Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 365,
    'summary': 'Payment Acquirer: Paypal Implementation',
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_paypal_templates.xml',
        'data/payment_acquirer_data.xml',
        'data/payment_paypal_email_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
