# -*- coding: utf-8 -*-

{
    'name': 'Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer Base Module',
    'description': """Payment Acquirer Base Module""",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'security/payment_security.xml',
        'data/payment_acquirer.xml',
        'views/payment_acquirer.xml',
        'views/assets.xml',
        'views/res_config_view.xml',
        'views/res_partner_view.xml',
    ],
    'auto_install': True,
}
