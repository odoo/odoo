# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stripe Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 395,
    'summary': 'Payment Provider: Stripe Implementation',
    'description': """Stripe Payment Provider""",
    'depends': ['payment'],
    'data': [
        'views/payment_stripe_templates.xml',
        'views/payment_templates.xml',  # Only load the SDK on pages with a payment form.
        'views/payment_views.xml',
        'data/payment_provider_data.xml',  # Depends on views/payment_stripe_templates.xml
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_stripe/static/src/js/express_checkout_form.js',
            'payment_stripe/static/src/js/payment_form.js',
        ],
    },
    'license': 'LGPL-3',
}
