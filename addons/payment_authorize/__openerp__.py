# -*- coding: utf-8 -*-

{
    'name': 'Authorize.Net Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Authorize.net Implementation',
    'version': '1.0',
    'description': """Authorize.Net Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/authorize.xml',
        'views/payment_acquirer.xml',
        'data/authorize.xml',
        'views/payment_authorize_template.xml',
    ],
    'installable': True,
}
