# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar_bis',
    'version': '1.1',
    'sequence': 5,
    'depends': ['web', 'base'],
    'summary': "Schedule employees' meetings",
    'description': """
This is a full-featured calendar system.
========================================

It supports:
------------
    - Calendar of events
    - Recurring events

If you need to manage your meetings, you should install the CRM module.
    """,
    'category': 'Productivity/Calendar2',
    'demo': [
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/calendar_security.xml',
        'views/calendar_timeslot_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'calendar_bis/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
