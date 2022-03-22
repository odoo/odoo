# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Acquirer: Razorpay",
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 385,
    'summary': "A Indian online payment provider covering 100+ payment methods.",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_razorpay_templates.xml',

        'data/payment_acquirer_data.xml',  # Depends on views/payment_razorpay_templates.xml
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
