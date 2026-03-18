# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'QFPay Payment Provider',
    'category': 'Accounting/Payment Providers',
    'summary': 'Secure eCommerce redirect for QFPay (Alipay, WeChat, Cards)',
    'description': " ",  # Non-empty string to avoid loading the README file.
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'depends': [
        'payment',
        'website_sale',
    ],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_qfpay_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_qfpay/static/src/interactions/payment_form.js',
        ],
    },
    'auto_install': True,
}
