# -*- coding: utf-8 -*-

{
    'name': 'Payment: Website Integration',
    'category': 'Website',
    'summary': 'Payment: Website Integration',
    'version': '1.0',
    'description': """Bridge module for acquirers and website.""",
    'author': 'OpenERP SA',
    'depends': [
        'website',
        'payment_acquirer',
    ],
    'data': [
        'views/website_payment_templates.xml',
    ],
    'auto_install': True,
}
