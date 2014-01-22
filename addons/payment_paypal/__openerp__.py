# -*- coding: utf-8 -*-

{
    'name': 'Paypal Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Paypal Implementation',
    'version': '1.0',
    'description': """Paypal Payment Acquirer""",
    'author': 'OpenERP SA',
    'depends': ['payment_acquirer'],
    'data': [
        'views/paypal.xml',
        'views/payment_acquirer.xml',
        'data/paypal.xml',
    ],
    'installable': True,
}
