# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Events Exhibitor Migration Layer',
    'version': '1.0',
    'category': 'Marketing/Events',
    'sequence': 9042,
    'summary': 'Provides a migration layer for v17.x databases',
    'depends': [
        'website_event_exhibitor',
        'website_event_migration_layer',
    ],
    'data': [
        'views/website_event_exhibitor.xml',
    ],
    'license': 'LGPL-3',
}
