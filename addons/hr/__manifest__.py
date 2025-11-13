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
        'web_hierarchy',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'data/report_paperformat.xml',
        'wizard/hr_departure_wizard_views.xml',
        'wizard/mail_activity_schedule_views.xml',
        'wizard/hr_bank_account_allocation_wizard.xml',
        'wizard/hr_bank_account_allocation_wizard_line.xml',
        'views/mail_activity_plan_views.xml',
        'views/hr_version_views.xml',
        'views/hr_contract_template_views.xml',
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
        'views/res_partner_bank_views.xml',
        'views/discuss_channel_views.xml',
        'views/res_users.xml',
        'views/hr_templates.xml',
        'data/hr_data.xml',
        'views/hr_export_mixin_views.xml',
    ],
    'demo': [
        'data/hr_demo.xml'
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web._assets_primary_variables': [
            'hr/static/src/scss/variables.scss',
        ],
        'web.assets_backend': [
            'hr/static/src/**/*',
            ('remove', 'hr/static/src/views/hr_employee_hierarchy/*'),
        ],
        'web.assets_backend_lazy': [
            'hr/static/src/views/hr_employee_hierarchy/*',
        ],
        'im_livechat.assets_embed_core': [
            'hr/static/src/core/common/**/*',
        ],
        'mail.assets_public': [
            'hr/static/src/core/common/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr/static/tests/legacy/**/*',
        ],
        'web.assets_unit_tests': [
            'hr/static/tests/**/*',
            'hr/static/tests/mock_server/mock_server.js',
            ('remove', 'hr/static/tests/tours/**/*'),
            ('remove', 'hr/static/tests/legacy/**/*'),
        ],
        'web.assets_tests': [
            'hr/static/tests/tours/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
