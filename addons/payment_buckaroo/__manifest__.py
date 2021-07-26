# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Buckaroo Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 355,
    'summary': 'Payment Acquirer: Buckaroo Implementation',
    'description': """Buckaroo Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_buckaroo_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
