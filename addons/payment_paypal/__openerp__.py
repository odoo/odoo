# -*- coding: utf-8 -*-

{
    'name': 'Paypal Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Paypal Implementation',
    'version': '1.0',
    'description': """Paypal Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/paypal.xml',
        'views/payment_acquirer.xml',
        'views/res_config_view.xml',
        'data/paypal.xml',
    ],
    'installable': True,
}
