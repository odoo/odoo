# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advanced Events',
    'category': 'Marketing',
    'summary': 'Sponsors, Tracks, Agenda, Event News',
    'version': '1.0',
    'description': "",
    'depends': ['website_event'],
    'data': [
        'security/ir.model.access.csv',
        'security/event_track_security.xml',
        'data/event_data.xml',
        'data/event_track_data.xml',
        'views/event_track_templates.xml',
        'views/event_track_views.xml',
        'views/event_sponsor_views.xml',
        'views/event_views.xml',
        'views/website_event_menu_views.xml',
        'views/event_menus.xml',
    ],
    'demo': [
        'data/event_demo.xml',
        'data/event_sponsor_demo.xml',
        'data/event_track_demo_misc.xml',
        'data/event_track_demo.xml',
        'data/event_track_demo_description.xml',
    ],
}
