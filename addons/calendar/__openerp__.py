# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar',
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
    'demo': ['data/calendar_demo.xml'],
    'data': [
        'data/calendar_cron.xml',
        'data/calendar_data.xml',
        'security/ir.model.access.csv',
        'security/calendar_security.xml',
        'views/calendar.xml',
        'views/calendar_view.xml'
    ],
    'test': [
        'test/calendar_test.yml',
        'test/test_calendar_recurrent_event_case2.yml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'application': True,
}
