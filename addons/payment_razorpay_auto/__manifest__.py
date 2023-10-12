# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Razorpay Auto",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 355,
    'summary': "A payment provider covering reccuring payments.",
    'depends': ['payment_razorpay'],
    'data': [
        'views/payment_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_razorpay_auto/static/src/js/payment_form.js',
        ],
    },
    "icon": "/payment_razorpay/static/description/icon.png",
    'license': 'LGPL-3',
}
