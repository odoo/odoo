# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Quiz on Live Event Tracks',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Bridge module to support quiz features during "live" tracks. ',
    'website': 'https://www.odoo.com/app/events',
    'description': "",
    'depends': [
        'website_event_track_live',
        'website_event_track_quiz',
    ],
    'data': [
        'views/event_track_templates_page.xml',
    ],
    'demo': [
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_event_track_live_quiz/static/src/js/**/*',
        ],
        'web.assets_qweb': [
            'website_event_track_live_quiz/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
