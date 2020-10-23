# -*- coding: utf-8 -*-

{
    'name': 'Ogone Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 360,
    'summary': 'Payment Acquirer: Ogone Implementation',
    'version': '1.0',
    'description': """Ogone Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/assets.xml',
        'views/payment_views.xml',
        'views/payment_ogone_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
