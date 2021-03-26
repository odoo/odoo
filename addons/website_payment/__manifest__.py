# -*- coding: utf-8 -*-

{
    'name': 'Website Payment',
    'category': 'Hidden',
    'summary': 'Payment integration with website',
    'version': '1.0',
    'description': """
This is a bridge module that adds multi-website support for payment acquirers.
    """,
    'depends': [
        'website',
        'payment',
        'portal',
    ],
    'data': [
        'views/payment_acquirer.xml',
    ],
    'auto_install': True,
}
