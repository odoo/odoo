# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Tracks Online',
    'category': 'Marketing/Events',
    'sequence': 1003,
    'version': '1.0',
    'summary': 'Bridge module to support Online Events Tracks',
    'website': 'https://www.odoo.com/page/events',
    'description': "",
    'depends': [
        'sms',
        'website_event_online',
        'website_event_track',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/event_event_views.xml',
        'views/event_sponsor_views.xml',
        'views/event_templates_registration.xml',
        'views/event_track_templates_reminder.xml',
        'views/event_track_templates.xml',
        'views/event_track_templates_reminder.xml',
        'views/event_track_views.xml',
        'views/event_track_tag_views.xml',
        'views/event_track_visitor_views.xml',
        'views/website_visitor_views.xml',
        'views/event_menus.xml',
    ],
    'demo': [
        'data/event_sponsor_demo.xml',
        'data/event_track_demo.xml',
        'data/event_track_tag_demo.xml',
        'data/event_track_visitor_demo.xml',
    ],
    'application': False,
    'installable': True,
}
