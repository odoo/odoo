# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Quiz on Live Event Tracks',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Bridge module to support quiz features during "live" tracks. ',
    'website': 'https://www.odoo.com/app/events',
    'depends': [
        'website_event_track_live',
        'website_event_track_quiz',
    ],
    'data': [
        'views/event_track_templates_page.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_event_track_live_quiz/static/src/js/event_quiz.js',
            'website_event_track_live_quiz/static/src/js/website_event_track_suggestion.js',
            'website_event_track_live_quiz/static/src/xml/website_event_track_quiz_templates.xml',
            'website_event_track_live_quiz/static/src/xml/website_event_track_live_templates.xml',
        ],
    },
    'license': 'LGPL-3',
}
