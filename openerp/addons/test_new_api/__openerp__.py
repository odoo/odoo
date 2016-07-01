# -*- coding: utf-8 -*-
{
    'name': 'Test API',
    'version': '1.0',
    'category': 'Tests',
    'description': """A module to test the API.""",
    'depends': ['base', 'web'],
    'installable': True,
    'auto_install': False,
    'data': [
        'ir.model.access.csv',
        'views.xml',
        'demo_data.xml',
    ],
}
