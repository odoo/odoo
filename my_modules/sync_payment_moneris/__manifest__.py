# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Moneris Checkout',
    'version': '16.0.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "Integration with Moneris Checkout Payment",
    'depends': [
        'payment', 'sale', 'account_payment'
    ],
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'https://www.synconics.com',
    'description': """
        Odoo Backend Integration with Moneris Checkout Payment Gateway
Moneris
Payment
Gateway
Moneris Payment
Backend Integration
Moneris payment
    """,
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_moneris_templates.xml',
        'views/sale_order_views.xml',
        'views/payment_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sync_payment_moneris/static/src/js/payment_form.js',
            'sync_payment_moneris/static/src/js/moneris_dialog.js',
            'sync_payment_moneris/static/src/js/post_processing.js',
            'sync_payment_moneris/static/src/xml/moneris_checkout.xml',
            'sync_payment_moneris/static/src/scss/moneris_dialog.scss',
        ],
    },
    'images': [
        'static/description/main_screen.png'
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'price': 300.0,
    'currency': 'USD',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
