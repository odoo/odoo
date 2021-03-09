# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar',
    'version': '1.0',
    'sequence': 165,
    'depends': ['base', 'mail'],
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
    'category': 'Productivity/Calendar',
    'demo': [
        'data/calendar_demo.xml'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/calendar_security.xml',
        'data/calendar_cron.xml',
        'data/calendar_data.xml',
        'data/mail_data_various.xml',
        'data/mail_template_data.xml',
        'views/mail_activity_views.xml',
        'views/calendar_templates.xml',
        'views/calendar_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            # inside .
            'calendar/static/src/scss/calendar.scss',
            # inside .
            'calendar/static/src/js/base_calendar.js',
            # inside .
            'calendar/static/src/js/calendar_renderer.js',
            # inside .
            'calendar/static/src/js/calendar_controller.js',
            # inside .
            'calendar/static/src/js/calendar_model.js',
            # inside .
            'calendar/static/src/js/calendar_view.js',
            # inside .
            'calendar/static/src/js/mail_activity.js',
            # inside .
            'calendar/static/src/js/systray_activity_menu.js',
        ],
        'web.qunit_suite_tests': [
            # after //script[last()]
            'calendar/static/tests/calendar_tests.js',
            # after //script[last()]
            'calendar/static/tests/systray_activity_menu_tests.js',
        ],
        'web.assets_qweb': [
            'calendar/static/src/xml/base_calendar.xml',
        ],
    }
}
