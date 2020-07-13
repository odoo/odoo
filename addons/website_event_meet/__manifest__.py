# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Event Meeting / Rooms',
    'category': 'Marketing/Events',
    'sequence': 1002,
    'version': '1.0',
    'summary': 'Event: meeting and chat rooms',
    'website': 'https://www.odoo.com/page/events',
    'description': "",
    'depends': [
        # STD-TODO: remove 'website_event_track'
        # we just need it to be able to use 'website.event.menu'
        # which is defined in 'website_event_track'
        'website_event_online',
        'website_event_track',
        'website_jitsi',
    ],
    'demo': ['data/website_event_meet_demo.xml'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/assets.xml',
        'views/event_templates.xml',
        'views/event_meeting_room_views.xml',
        'views/event_meet_template_meet.xml',
        'views/event_views.xml',
        'views/event_type_views.xml',
    ],
    'application': False,
    'installable': True,
}
