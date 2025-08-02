# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employees',
    'version': '1.1',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Centralize employee information',
    'website': 'https://www.odoo.com/app/employees',
    'images': [
        'static/src/img/default_image.png',
    ],
    'depends': [
        'base_setup',
        'phone_validation',
        'mail',
        'resource',
        'web',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_departure_wizard_views.xml',
        'wizard/mail_activity_schedule_views.xml',
        'views/mail_activity_plan_views.xml',
        'views/hr_departure_reason_views.xml',
        'views/hr_contract_type_views.xml',
        'views/hr_job_views.xml',
        'views/hr_employee_category_views.xml',
        'views/hr_employee_public_views.xml',
        'report/hr_employee_badge.xml',
        'views/hr_employee_views.xml',
        'views/hr_department_views.xml',
        'views/hr_work_location_views.xml',
        'views/hr_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/discuss_channel_views.xml',
        'views/res_users.xml',
        'views/hr_templates.xml',
        'data/hr_data.xml',
    ],
    'demo': [
        'data/hr_demo.xml'
    ],
    'installable': True,
    'application': True,
    'post_init_hook': '_install_hr_localization',
    'assets': {
        'web.assets_backend': [
            'hr/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr/static/tests/**/*',
            ('remove', 'hr/static/tests/tours/**/*'),
        ],
        'web.assets_tests': [
            'hr/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
