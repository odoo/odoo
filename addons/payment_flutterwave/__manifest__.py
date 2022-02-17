# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Flutterwave Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 360,
    'summary': 'Payment Acquirer: Flutterwave Implementation',
    'description': """Flutterwave Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_flutterwave_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
