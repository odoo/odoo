# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Razorpay Oauth",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider covering India.",
    'description': "Quick onboarding with razorpay",
    'depends': ['payment', 'payment_razorpay'],
    'data': [
        'views/payment_provider_views.xml',

        'data/ir_cron_data.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
