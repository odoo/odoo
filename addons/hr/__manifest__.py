# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employees',
    'version': '1.1',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Centralize employee information',
    'description': "",
    'website': 'https://www.odoo.com/page/employees',
    'images': [
        'images/hr_department.jpeg',
        'images/hr_employee.jpeg',
        'images/hr_job_position.jpeg',
        'static/src/img/default_image.png',
    ],
    'depends': [
        'base_setup',
        'mail',
        'resource',
        'web',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_plan_wizard_views.xml',
        'wizard/hr_departure_wizard_views.xml',
        'views/hr_departure_reason_views.xml',
        'views/hr_job_views.xml',
        'views/hr_plan_views.xml',
        'views/hr_employee_category_views.xml',
        'views/hr_employee_public_views.xml',
        'report/hr_employee_badge.xml',
        'views/hr_employee_views.xml',
        'views/hr_department_views.xml',
        'views/hr_work_location_views.xml',
        'views/hr_views.xml',
        'views/res_config_settings_views.xml',
        'views/mail_channel_views.xml',
        'views/res_users.xml',
        'data/hr_data.xml',
    ],
    'demo': [
        'data/hr_demo.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'hr/static/src/scss/hr.scss',
            'hr/static/src/bugfix/bugfix.scss',
            'hr/static/src/bugfix/bugfix.js',
            'hr/static/src/js/chat.js',
            'hr/static/src/js/language.js',
            'hr/static/src/js/many2one_avatar_employee.js',
            'hr/static/src/js/standalone_m2o_avatar_employee.js',
            'hr/static/src/models/employee/employee.js',
            'hr/static/src/models/messaging/messaging.js',
            'hr/static/src/models/partner/partner.js',
            'hr/static/src/models/user/user.js',
        ],
        'web.qunit_suite_tests': [
            'hr/static/src/bugfix/bugfix_tests.js',
            'hr/static/tests/helpers/mock_models.js',
            'hr/static/tests/many2one_avatar_employee_tests.js',
            'hr/static/tests/standalone_m2o_avatar_employee_tests.js',
        ],
        'web.assets_qweb': [
            'hr/static/src/bugfix/bugfix.xml',
            'hr/static/src/xml/hr_templates.xml',
        ],
    }
}
