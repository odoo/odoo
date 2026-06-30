# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Toss Payments",
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider covering the South Korea market",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
        'views/payment_toss_payments_templates.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {'web.assets_frontend': ['payment_toss_payments/static/src/**/*']},
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
