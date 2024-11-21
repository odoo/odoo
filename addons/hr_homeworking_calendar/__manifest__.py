# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Remote Work with calendar',
    'version': '1.0',
    'category': 'Human Resources/Remote Work',
    'depends': ['hr_homeworking', 'calendar'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/homework_location_wizard.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_homeworking_calendar/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr_homeworking_calendar/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
