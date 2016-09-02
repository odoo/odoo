# -*- coding: utf-8 -*-

{
    'name': 'Buckaroo Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Buckaroo Implementation',
    'version': '1.0',
    'description': """Buckaroo Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_buckaroo_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
}
