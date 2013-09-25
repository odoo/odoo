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
        'event_data.xml',
        'views/website_event.xml',
        'security/ir.model.access.csv',
        'security/website_event.xml',
        'event_demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [],
    'installable': True,
}
