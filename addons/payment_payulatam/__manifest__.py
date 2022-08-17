# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuLatam Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 380,
    'summary': "This module is deprecated.",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_payulatam_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': False,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
