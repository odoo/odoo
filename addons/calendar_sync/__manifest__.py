# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar Syncer',
    'version': '1.0',
    'depends': ['calendar'],
    'summary': "Sync Odoo calendar with external calendar services.",
    'description': """
    This module provides a generic structure to handle external calendar services synchronization with Odoo.
    It manages the interface with the front-end and dispatch requests to the calendar service provider selected by
    the current user.
    """,
    'category': 'Productivity/Calendar',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'data/calendar_sync_data.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'calendar_sync/static/src/js/calendar_sync.js',
        ],
    },
    'license': 'LGPL-3',
}
