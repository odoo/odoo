# -*- coding: utf-8 -*-
{
    'name': 'Download Action',
    'category': 'Base',
    'summary': 'File Download Action',
    'version': '0.1',
    'description': """File Download Action""",
    'author': 'Naglis Jonaitis',
    'depends': ['web'],
    'js': [
        'static/src/js/download_action.js'
    ],
    'data': [
        'views/download_action.xml',
        'data/data.xml',
    ],
    'installable': True,
    'auto_install': False,
}
