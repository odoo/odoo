# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Events Track Migration Layer',
    'version': '1.0',
    'category': 'Marketing/Events',
    'sequence': 9040,
    'summary': 'Provides a migration layer for v17.x databases',
    'depends': [
        'website_event_track',
        'website_event_migration_layer',
    ],
    'data': [
        'views/website_event_track.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_event_track_migration_layer/static/src/js/website_event_track.js',
        ],
    },
    'license': 'LGPL-3',
}
