# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event / Jitsi',
    'category': 'Marketing/Events',
    'sequence': 1002,
    'version': '1.0',
    'summary': 'Event / Jitsi',
    'website': 'https://www.odoo.com/app/events',
    'depends': [
        'website_event',
        'website_discuss_room',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_event_jitsi/static/src/js/chat_room.js',
        ],
    },
    'license': 'LGPL-3',
}
