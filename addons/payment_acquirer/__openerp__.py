# -*- coding: utf-8 -*-

{
    'name': 'Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer Base Module',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'author': 'OpenERP SA',
    'depends': ['mail'],
    'data': [
        'views/payment_acquirer.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
