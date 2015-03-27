# -*- coding: utf-8 -*-

{
    'name': 'Alipay Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Alipay Implementation',
    'version': '1.0',
    'description': """Alipay Payment Acquirer""",
    'author': 'Odoo CN, Jeffery',
    'depends': ['payment'],
    'data': [
        'views/alipay.xml',
        'views/payment_acquirer.xml',
        'views/res_config_view.xml',
        'data/alipay.xml',
    ],
    'installable': True,
}
