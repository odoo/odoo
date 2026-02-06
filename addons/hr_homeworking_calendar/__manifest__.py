# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Remote Work with calendar',
    'category': 'Human Resources/Remote Work',
    'depends': ['hr_homeworking', 'calendar'],
    'data': [
        'wizard/homework_location_wizard.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_homeworking_calendar/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_homeworking_calendar/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
