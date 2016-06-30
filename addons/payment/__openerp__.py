# -*- coding: utf-8 -*-

{
    'name': 'Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer Base Module',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['account'],
    'data': [
        'views/payment_acquirer.xml',
        'views/res_config_view.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
        'security/payment_security.xml',
    ],
    'installable': True,
    'auto_install': True,
}
