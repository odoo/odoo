# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Events Migration Layer',
    'version': '1.0',
    'category': 'Marketing/Events',
    'sequence': 9040,
    'summary': 'Provides a migration layer for v17.x databases',
    'depends': [
        'website_event',
    ],
    'data': [
        'views/website_event.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            ('before', 'website_event/static/src/scss/event_templates_common.scss', 'website_event_migration_layer/static/src/scss/website_event_migration_layer.scss'),
        ],
    },
    'license': 'LGPL-3',
}
