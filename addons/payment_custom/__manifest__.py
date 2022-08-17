# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Custom Payment Modes',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Payment Provider: Custom payment modes',
    'depends': ['payment'],
    'data': [
        'views/payment_custom_templates.xml',
        'views/payment_views.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_custom/static/src/js/post_processing.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
