# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "Website Jitsi",
    'category': 'Hidden',
    'version': '1.0',
    "summary": "Create Jitsi room on website.",
    'website': 'https://www.odoo.com/app/events',
    "description": "Create Jitsi room on website.",
    "depends": [
        "website"
    ],
    "data": [
        'views/chat_room_templates.xml',
        'views/chat_room_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_jitsi/static/src/css/chat_room.css',
            'website_jitsi/static/src/js/chat_room.js',
            'website_jitsi/static/src/xml/chat_room_modal.xml',
        ],
    },
    'license': 'LGPL-3',
}
