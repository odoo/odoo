# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Wire Transfer Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Payment Acquirer: Wire Transfer Implementation',
    'description': """Wire Transfer Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_transfer_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'auto_install': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
