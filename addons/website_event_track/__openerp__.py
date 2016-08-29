# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advanced Events',
    'category': 'Marketing',
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
        'security/ir.model.access.csv',
        'security/website_event_track_security.xml',
        'data/website_event_track_data.xml',
        'views/website_event_track_templates.xml',
        'views/website_event_track_views.xml',
        'views/event_views.xml',
    ],
    'demo': [
        'data/event_demo.xml',
        'data/website_event_track_demo.xml'
    ],
}
