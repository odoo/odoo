# -*- coding: utf-8 -*-
{
    'name': 'Website Tracking',
    'category': 'Website',
    'summary': 'Track your users activity',
    'version': '1.0',
    'description': "",
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/snippets.xml',
        'views/templates.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
