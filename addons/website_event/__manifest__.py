# -*- coding: utf-8 -*-

{
    'name': 'Online Events',
    'category': 'Marketing',
    'sequence': 135,
    'summary': 'Publish Events and Manage Online Registrations on your Website',
    'website': 'https://www.odoo.com/page/website-builder',
    'description': """
Online Events
        """,
    'depends': ['website', 'website_partner', 'website_mail', 'event'],
    'data': [
        'data/event_data.xml',
        'views/event_config_settings_views.xml',
        'views/event_templates.xml',
        'views/event_views.xml',
        'security/ir.model.access.csv',
        'security/event_security.xml',
    ],
    'demo': [
        'data/event_demo.xml'
    ],
    'application': True,
}
