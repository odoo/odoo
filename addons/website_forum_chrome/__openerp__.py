# -*- coding: utf-8 -*-

{
    'name': 'Chrome extension for forum',
    'version': '1.0',
    'category': 'Website',
    'description': """
Submit Links to Forum
======================

This module lets you submit the URL to your forum.
    """,
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com',
    'images': [],
    'depends': ['website_forum'],
    'data': [
             'views/forum_chrome.xml',
             'views/website_forum_chrome.xml',
             'views/website_forum_chrome_template.xml'
    ],
    'installable': True,
}
