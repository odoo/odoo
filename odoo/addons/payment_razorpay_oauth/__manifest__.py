# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Razorpay OAuth Integration",
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "Easy Razorpay Onboarding With Oauth.",
    'icon': '/payment_razorpay/static/description/icon.png',
    'depends': ['payment_razorpay'],
    'data': [
        'views/payment_provider_views.xml',
        'views/razorpay_templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
