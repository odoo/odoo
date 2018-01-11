# -*- coding: utf-8 -*-

{
    'name': 'Online Events',
    'category': 'Website',
    'summary': 'Schedule, Promote and Sell Events',
    'website': 'https://www.odoo.com/page/website-builder',
    'version': '1.0',
    'description': """
Online Events
        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'website_partner', 'website_mail', 'event'],
    'data': [
        'data/event_data.xml',
        'views/website_event.xml',
        'views/website_event_sale_backend.xml',
        'security/ir.model.access.csv',
        'security/website_event.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [
        'data/event_demo.xml'
    ],
    'installable': True,
    'application': True,
}
