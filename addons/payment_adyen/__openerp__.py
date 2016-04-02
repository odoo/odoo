# -*- coding: utf-8 -*-

{
    'name': 'Adyen Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Adyen Implementation',
    'version': '1.0',
    'description': """Adyen Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/adyen.xml',
        'views/payment_acquirer.xml',
        'data/adyen.xml',
    ],
    'installable': True,
}
