# -*- coding: utf-8 -*-

{
    'name': 'Online Events',
    'category': 'Website',
    'sequence': 135,
    'summary': 'Schedule, Promote and Sell Events',
    'website': 'https://www.odoo.com/page/website-builder',
    'version': '1.0',
    'description': """
Online Events
        """,
    'depends': ['website', 'website_partner', 'website_mail', 'event'],
    'data': [
        'data/website_event_data.xml',
        'views/website_event_templates.xml',
        'views/website_event_views.xml',
        'security/ir.model.access.csv',
        'security/website_event_security.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [
        'data/website_event_demo.xml'
    ],
    'installable': True,
    'application': True,
}
