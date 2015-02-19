# -*- coding: utf-8 -*-

{
    'name': 'Website Gengo Translator',
    'category': 'Website',
    'version': '1.0',
    'description': """
Website Gengo Translator
========================

Translate you website in one click
""",
    'author': 'Odoo SA',
    'depends': [
        'website',
        'base_gengo'
    ],
    'data': [
        'views/website_gengo.xml',
    ],
    'installable': True,
}
