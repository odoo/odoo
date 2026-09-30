{
    'name': 'Holidays with Remote Work',
    'category': 'Human Resources',
    'summary': 'Manage holidays with remote work',
    'depends': [
        'hr_holidays',
        'hr_homeworking',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_holidays_homeworking/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_holidays_homeworking/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'auto_install': True,
}
