# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Enterprise Event Track',
    'category': 'Marketing',
    'summary': 'Advanced Event Track Management',
    'version': '1.0',
    'description': """This module helps analyzing and organizing event tracks.
For that purpose it adds a gantt view on event tracks.""",
    'depends': ['website_event_track', 'web_gantt'],
    'auto_install': True,
    'data': [
        'views/event_event_views.xml',
        'views/event_track_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'website_event_track_gantt/static/src/**/*.js',
        ],
    },
    'license': 'OEEL-1',
}
