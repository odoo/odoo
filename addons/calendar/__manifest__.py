# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar',
    'version': '1.0',
    'sequence': 130,
    'depends': ['base', 'mail'],
    'summary': 'Schedule employees meetings',
    'description': """
This is a full-featured calendar system.
========================================

It supports:
------------
    - Calendar of events
    - Recurring events

If you need to manage your meetings, you should install the CRM module.
    """,
    'category': 'Extra Tools',
    'demo': [
        'data/calendar_demo.xml'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/calendar_security.xml',
        'data/calendar_cron.xml',
        'data/calendar_data.xml',
        'data/mail_data.xml',
        'views/mail_activity_views.xml',
        'views/calendar_templates.xml',
        'views/calendar_views.xml',
        'data/mail_activity_data.xml',
    ],
    'qweb': ['static/src/xml/base_calendar.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
