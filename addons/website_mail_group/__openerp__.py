# -*- coding: utf-8 -*-

{
    'name': 'Mailing List Archive',
    'category': 'Website',
    'summary': '',
    'version': '1.0',
    'description': """
OpenERP Mail Group : Mailing List Archives
==========================================

        """,
    'author': 'Odoo SA',
    'depends': ['website_mail'],
    'data': [
        'views/website_mail_group.xml',
        'views/snippets.xml',
    ],
    'installable': True,
}
