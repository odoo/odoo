# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Outlook Calendar',
    'version': '1.0',
    'category': 'Productivity',
    'depends': ['microsoft_account', 'calendar'],
    'data': [
        'data/microsoft_calendar_data.xml',
        'security/microsoft_calendar_security.xml',
        'security/ir.model.access.csv',
        'wizard/reset_account_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/microsoft_calendar_views.xml',
        ],
    'installable': True,
    'post_init_hook': 'init_initiating_microsoft_uuid',
    'assets': {
        'web.assets_backend': [
            'microsoft_calendar/static/src/scss/microsoft_calendar.scss',
            'microsoft_calendar/static/src/views/**/*',
        ],
        'web.qunit_suite_tests': [
            'microsoft_calendar/static/tests/microsoft_calendar_mock_server.js',
            'microsoft_calendar/static/tests/microsoft_calendar_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'microsoft_calendar/static/tests/microsoft_calendar_mock_server.js',
        ],
    },
    'license': 'LGPL-3',
}
