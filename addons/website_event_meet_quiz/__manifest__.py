# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Quiz and Meet on community',
    'category': 'Marketing/Events',
    'sequence': 1007,
    'version': '1.0',
    'summary': 'Quiz and Meet on community route',
    'website': 'https://www.odoo.com/page/events',
    'description': "",
    'depends': [
        'website_event_meet',
        'website_event_track_quiz',
    ],
    'data': [
        'views/event_meet_templates.xml',
    ],
    'demo': [
    ],
    'application': False,
    'auto_install': True,
}
