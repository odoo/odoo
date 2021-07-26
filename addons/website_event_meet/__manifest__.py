# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Event Meeting / Rooms',
    'category': 'Marketing/Events',
    'sequence': 1002,
    'version': '1.0',
    'summary': 'Event: meeting and chat rooms',
    'website': 'https://www.odoo.com/app/events',
    'description': "",
    'depends': [
        'website_event',
        'website_jitsi',
    ],
    'demo': ['data/website_event_meet_demo.xml'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/event_meet_templates_list.xml',
        'views/event_meet_templates_page.xml',
        'views/event_meeting_room_views.xml',
        'views/event_event_views.xml',
        'views/event_type_views.xml',
    ],
    'application': False,
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'website_event_meet/static/src/scss/event_meet_templates.scss',
            'website_event_meet/static/src/js/customize_options.js',
            'website_event_meet/static/src/js/website_event_meeting_room.js',
            'website_event_meet/static/src/js/website_event_create_meeting_room_button.js',
        ],
    },
    'license': 'LGPL-3',
}
