# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Quiz on Live Event Tracks',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Bridge module to support quiz features during "live" tracks. ',
    'website': 'https://www.odoo.com/page/events',
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
            # after //script[last()]
            'website_event_track_live_quiz/static/src/js/website_event_track_suggestion.js',
            # after //script[last()]
            'website_event_track_live_quiz/static/src/js/event_quiz.js',
        ],
        'web.assets_qweb': [
            'website_event_track_live_quiz/static/src/xml/website_event_track_live_templates.xml',
            'website_event_track_live_quiz/static/src/xml/website_event_track_quiz_templates.xml',
        ],
    }
}
