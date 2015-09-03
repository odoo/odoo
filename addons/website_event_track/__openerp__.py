# -*- coding: utf-8 -*-

{
    'name': 'Advanced Events',
    'category': 'Website',
    'summary': 'Sponsors, Tracks, Agenda, Event News',
    'website': 'https://www.odoo.com/page/events',
    'version': '1.0',
    'description': """
Online Advanced Events
======================

Adds support for:
- sponsors
- dedicated menu per event
- news per event
- tracks
- agenda
- call for proposals
        """,
    'depends': ['website_event'],
    'data': [
        'data/website_event_track_data.xml',
        'views/website_event_track_templates.xml',
        'views/website_event_track_views.xml',
        'data/website_event_track_tip_data.xml',
        'security/ir.model.access.csv',
        'security/website_event_track_security.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [
        'data/event_demo.xml',
        'data/website_event_track_demo.xml'
    ],
    'installable': True,
}
