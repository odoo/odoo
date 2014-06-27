# -*- coding: utf-8 -*-

{
    'name': 'CCAvenue Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: CCAvenue Implementation',
    'version': '1.0',
    'description': """CCAvenue Payment Acquirer""",
    'author': 'OpenERP SA',
    'depends': ['payment'],
    'data': [
        'views/ccavenue.xml',
        'views/payment_acquirer.xml',
        'data/ccavenue.xml',
    ],
    'installable': True,
}
