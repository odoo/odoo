# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Hyperpay',
    'version': '0.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 45,
    'summary': "Integration with Hyperpay Checkout Payment",
    'depends': [
        'payment', 'account', 'website', 'website_sale'
    ],
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'https://www.synconics.com',
    'description': """
    """,
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_hyperpay_templates.xml',
        'data/ir_cron.xml',
        'data/payment_provider_data.xml',
    ],
    'images': ['hyperpay/static/description/hyperpay_icon.png'],
    'assets': {
        'web.assets_frontend': [
            'hyperpay/static/src/*/*.js',
            'hyperpay/static/src/*/*.xml',
            'hyperpay/static/src/*/*.css',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'price': 300.0,
    'currency': 'USD',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
