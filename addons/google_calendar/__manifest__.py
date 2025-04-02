# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google Calendar',
    'version': '1.0',
    'category': 'Productivity',
    'depends': ['google_account', 'calendar'],
    'data': [
        'data/google_calendar_data.xml',
        'wizard/reset_account_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/google_calendar_views.xml',
        'security/ir.access.csv',
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
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
