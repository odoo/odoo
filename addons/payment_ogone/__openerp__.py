# -*- coding: utf-8 -*-

{
    'name': 'Ogone Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Ogone Implementation',
    'version': '1.0',
    'description': """Ogone Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/ogone.xml',
        'views/payment_acquirer.xml',
        'data/ogone.xml',
    ],
    'installable': True,
}
