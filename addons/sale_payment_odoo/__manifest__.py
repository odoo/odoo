# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Odoo Payments',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 330,
    'summary': 'Payment Acquirer: Odoo Payments',
    'description': """Sale Odoo Payments integration: show SO on payment transactions.""",
    'depends': ['payment_odoo', 'sale'],
    'data': [
        'views/adyen_transaction_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
