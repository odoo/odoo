# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ogone Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 360,
    'summary': 'Payment Acquirer: Ogone Implementation',
    'description': """Ogone Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_ogone_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
