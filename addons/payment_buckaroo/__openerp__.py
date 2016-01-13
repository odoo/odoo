# -*- coding: utf-8 -*-

{
    'name': 'Buckaroo Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Buckaroo Implementation',
    'version': '1.0',
    'description': """Buckaroo Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/buckaroo_templates.xml',
        'views/payment_acquirer.xml',
        'data/buckaroo_data.xml',
    ],
    'installable': True,
}
