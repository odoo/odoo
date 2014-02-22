# -*- coding: utf-8 -*-

{
    'name': 'Forum',
    'category': 'Website',
    'summary': 'Ask Questions and give Answers',
    'version': '1.0',
    'description': """
Ask questions, get answers, no distractions
        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'website_mail'],
    'data': [
         'data/forum_data.xml',
         'views/website_forum.xml',
         'security/ir.model.access.csv',
         'security/website_forum.xml',
    ],
    'qweb': [
         'static/src/xml/*.xml'
    ],
    'demo': [
        'data/forum_demo.xml'
    ],
    'installable': True,
    'application': True,
}
