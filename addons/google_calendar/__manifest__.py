# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google Calendar',
    'version': '1.0',
    'category': 'Productivity',
    'description': "",
    'depends': ['google_account', 'calendar'],
    'data': [
        'data/google_calendar_data.xml',
        'security/ir.model.access.csv',
        'wizard/reset_account_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/google_calendar_views.xml',
        ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            # inside .
            'google_calendar/static/src/js/google_calendar_popover.js',
            # inside .
            'google_calendar/static/src/js/google_calendar.js',
            # after link[last()]
            'google_calendar/static/src/scss/google_calendar.scss',
        ],
        'web.qunit_suite_tests': [
            # inside .
            'google_calendar/static/tests/mock_server.js',
            # inside .
            'google_calendar/static/tests/google_calendar_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            # inside .
            'google_calendar/static/tests/mock_server.js',
        ],
        'web.assets_qweb': [
            'google_calendar/static/src/xml/*.xml',
        ],
    }
}
