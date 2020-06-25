# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Event Live Sessions',
    'category': 'Marketing/Events',
    'sequence': 1005,
    'version': '1.0',
    'summary': 'Event: live session on tracks',
    'website': 'https://www.odoo.com/page/events',
    'description': "",
    'depends': [
        'website_event_track_online',
    ],
    'data': [
        'views/assets.xml',
        'views/event_track_templates.xml',
        'views/event_track_templates_misc.xml',
        'views/event_track_templates_track.xml',
        'views/event_track_views.xml',
    ],
    'demo': [
        'data/event_track_demo.xml',
    ],
    'application': False,
    'installable': True,
}
