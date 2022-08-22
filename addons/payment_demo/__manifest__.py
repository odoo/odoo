# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Demo Payment Acquirer',
    'version': '2.0',
    'category': 'Hidden',
    'description': """
This module adds a simple payment acquirer allowing to make demo payments.
It should never be used in production environment. Make sure to disable it before going live.
""",
    'depends': ['payment'],
    'data': [
        'views/payment_demo_templates.xml',
        'views/payment_templates.xml',
        'views/payment_token_views.xml',
        'views/payment_transaction_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_demo/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}
