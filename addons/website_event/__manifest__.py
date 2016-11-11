# -*- coding: utf-8 -*-

{
    'name': 'Online Events',
    'category': 'Marketing',
    'sequence': 135,
    'summary': 'Schedule, Promote and Sell Events',
    'website': 'https://www.odoo.com/page/website-builder',
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
    'demo': [
        'data/website_event_demo.xml'
    ],
    'application': True,
}
