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
        'digest',
        'phone_validation',
        'resource_mail',
        'web',
        'hr_base',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'data/report_paperformat.xml',
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
            ('remove', 'hr/static/src/views/hr_graph_view.js'),
            ('remove', 'hr/static/src/views/hr_graph_controller.xml'),
            ('remove', 'hr/static/src/views/hr_pivot_view.js'),
            ('remove', 'hr/static/src/views/hr_pivot_controller.xml'),
        ],
        'web.assets_backend_lazy': [
            'hr/static/src/views/hr_graph_view.js',
            'hr/static/src/views/hr_graph_controller.xml',
            'hr/static/src/views/hr_pivot_view.js',
            'hr/static/src/views/hr_pivot_controller.xml',
        ],
        'web.qunit_suite_tests': [
            'hr/static/tests/legacy/**/*',
        ],
        'web.assets_unit_tests': [
            'hr/static/tests/**/*',
            ('remove', 'hr/static/tests/tours/**/*'),
            ('remove', 'hr/static/tests/legacy/**/*'),
        ],
        'web.assets_tests': [
            'hr/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
