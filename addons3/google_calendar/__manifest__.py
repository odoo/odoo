# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google Calendar',
    'version': '1.0',
    'category': 'Productivity',
    'depends': ['google_account', 'calendar'],
    'data': [
        'data/google_calendar_data.xml',
        'security/google_calendar_security.xml',
        'security/ir.model.access.csv',
        'wizard/reset_account_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/google_calendar_views.xml',
        ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'google_calendar/static/src/scss/google_calendar.scss',
            'google_calendar/static/src/views/**/*',
        ],
        'web.qunit_suite_tests': [
            'google_calendar/static/tests/**/*',
        ],
        'web.qunit_mobile_suite_tests': [
            'google_calendar/static/tests/google_calendar_mock_server.js',
        ],
    },
    'license': 'LGPL-3',
}
