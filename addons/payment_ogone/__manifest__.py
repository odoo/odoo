# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ogone Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 370,
    'summary': "This module is deprecated.",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_ogone_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': False,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
