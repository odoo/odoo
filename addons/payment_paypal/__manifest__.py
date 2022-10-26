# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Paypal',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "An American payment provider for online payments all over the world.",
    'depends': ['payment'],
    'data': [
        'views/payment_paypal_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',

        'data/payment_provider_data.xml',
        'data/payment_paypal_email_data.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
