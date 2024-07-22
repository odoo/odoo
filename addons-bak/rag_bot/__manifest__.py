# -*- coding: utf-8 -*-
{
    'name': "Rag Bot",

    'summary': """
        
    """,

    'description': """
        
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com/",
    'category': 'Services/RagBot',
    'version': '0.1',
    'application': True,
    'installable': True,
    'depends': ['base', 'web'],

    'data': [
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rag_bot/static/src/**/*',
        ],
    },
    'license': 'AGPL-3'
}
