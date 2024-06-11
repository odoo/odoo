# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Remote Work',
    'version': '1.0',
    'category': 'Human Resources/Remote Work',
    'depends': ['hr', 'calendar'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/res_users.xml',
        'wizard/homework_location_wizard.xml',
    ],
    'demo': [
        'data/hr_homeworking_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'hr_homeworking/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr_homeworking/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
