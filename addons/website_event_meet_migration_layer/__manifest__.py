# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Events Meet Migration Layer',
    'version': '1.0',
    'category': 'Marketing/Events',
    'sequence': 9040,
    'summary': 'Provides a migration layer for v17.x databases',
    'depends': [
        'website_event_meet',
        'website_event_migration_layer',
    ],
    'data': [
        'views/website_event_meet.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_event_meet_migration_layer/static/src/xml/website_event_meet.xml',
        ],
    },
    'license': 'LGPL-3',
}
