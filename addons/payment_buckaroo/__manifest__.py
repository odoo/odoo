# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Buckaroo Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 355,
    'summary': 'Payment Provider: Buckaroo Implementation',
    'description': """Buckaroo Payment Provider""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_buckaroo_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
