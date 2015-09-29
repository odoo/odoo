# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar',
    'version': '1.0',
    'sequence': 130,
    'depends': ['base', 'mail', 'base_action_rule', 'web_calendar'],
    'summary': 'Personal & Shared Calendar',
    'description': """
This is a full-featured calendar system.
========================================

It supports:
------------
    - Calendar of events
    - Recurring events

If you need to manage your meetings, you should install the CRM module.
    """,
    'category': 'Hidden/Dependency',
    'website': 'https://www.odoo.com/page/crm',
    'demo': ['calendar_demo.xml'],
    'data': [
        'calendar_cron.xml',
        'security/ir.model.access.csv',
        'security/calendar_security.xml',
        'calendar_view.xml',
        'calendar_data.xml',
        'views/calendar.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'test': [
        'test/calendar_test.yml',
        'test/test_calendar_recurrent_event_case2.yml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
