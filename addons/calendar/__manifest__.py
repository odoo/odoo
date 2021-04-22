# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar',
    'version': '1.1',
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
        'data/mail_template_data.xml',
        'data/calendar_data.xml',
        'data/mail_data_various.xml',
        'views/mail_activity_views.xml',
        'views/calendar_templates.xml',
        'views/calendar_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'calendar/static/src/models/activity/activity.js',
            'calendar/static/src/components/activity/activity.js',
            'calendar/static/src/scss/calendar.scss',
            'calendar/static/src/js/base_calendar.js',
            'calendar/static/src/js/calendar_renderer.js',
            'calendar/static/src/js/calendar_controller.js',
            'calendar/static/src/js/calendar_model.js',
            'calendar/static/src/js/calendar_view.js',
            'calendar/static/src/js/systray_activity_menu.js',
            'calendar/static/src/js/services/calendar_notification_service.js',
        ],
        'web.qunit_suite_tests': [
            'calendar/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'calendar/static/src/xml/base_calendar.xml',
            'calendar/static/src/components/activity/activity.xml',
        ],
    },
    'license': 'LGPL-3',
}
