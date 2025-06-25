# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Display Working Hours in Calendar",
    'version': '1.0',
    'category': 'Human Resources/Employees',
    'depends': ['hr', 'calendar'],
    'auto_install': True,
    'data': [
        'views/calendar_views_calendarApp.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_calendar/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr_calendar/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
