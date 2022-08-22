# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Alipay Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'version': '2.0',
    'sequence': 345,
    'summary': "This module is deprecated.",
    'depends': ['payment'],
    'data': [
        'views/payment_alipay_templates.xml',
        'views/payment_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': False,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
