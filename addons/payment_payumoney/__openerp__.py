# -*- coding: utf-8 -*-

{
    'name': 'PayuMoney Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: PayuMoney Implementation',
    'version': '1.0',
    'description': """PayuMoney Payment Acquirer""",
    'author': 'Odoo SA',
    'depends': ['payment'],
    'data': [
        'views/payumoney.xml',
        'views/payment_acquirer.xml',
        'data/payu.xml',
    ],
    'installable': True,
}
