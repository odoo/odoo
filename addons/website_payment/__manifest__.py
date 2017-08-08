# -*- coding: utf-8 -*-

{
    'name': 'Payment: Website Integration',
    'category': 'Website',
    'summary': 'Payment: Website Integration',
    'version': '1.0',
    'description': """Bridge module for acquirers and website.""",
    'depends': [
        'website',
        'payment',
        'portal',
    ],
    'data': [
        'views/website_payment_view.xml',
        'views/website_payment_templates.xml',
    ],
    'auto_install': False,
}
