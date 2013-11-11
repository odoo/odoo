# -*- coding: utf-8 -*-

{
    'name': 'Online Events',
    'category': 'Website',
    'summary': 'Schedule, Promote and Sell Events',
    'version': '1.0',
    'description': """
Online Events
=============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'website_mail', 'event_sale', 'website_sale'],
    'data': [
        'data/event_data.xml',
        'views/website_event.xml',
        'views/website_event_sale_backend.xml',
        'security/ir.model.access.csv',
        'security/website_event.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [
        'data/event_demo.xml',
        'demo/website_event_homepage_demo.xml',
    ],
    'installable': True,
}
