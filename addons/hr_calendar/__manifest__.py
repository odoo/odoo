# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Display Working Hours in Calendar",
    'category': 'Human Resources/Employees',
    'depends': ['hr', 'calendar'],
    'auto_install': True,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/calendar_views.xml',
        'views/calendar_views_calendarApp.xml',
        'views/res_partner_views.xml',
        'wizard/homework_location_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_calendar/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_calendar/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
