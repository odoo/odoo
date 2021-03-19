# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    # TODO rename and stuff
    'name': 'Odoo Payments Sale',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 330,
    'summary': 'Payment Acquirer: Odoo Payments',
    'description': """Odoo Payments Sale integration""",
    'depends': ['payment_odoo', 'sale'],
    'data': [
        'views/adyen_transaction_views.xml',
    ],
    'auto_install': True,
}
