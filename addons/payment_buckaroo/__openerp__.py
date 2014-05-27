# -*- coding: utf-8 -*-

{
    'name': 'Payment Buckaroo',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Buckaroo Implementation',
    'version': '1.0',
    'description': """Payment Buckaroo""",
    'author': 'OpenERP SA',
    'depends': ['payment'],
    'data': [
        'views/buckaroo.xml',
        'views/payment_acquirer.xml',
        'data/buckaroo.xml',
    ],
    'installable': True,
}
