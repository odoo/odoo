# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator',
    'category': 'Human Resources',
    'summary': 'Sign Employment Contracts',
    'version': '2.0',
    'depends': [
        'hr_contract_sign',
        'hr_contract_reports',
        'http_routing',
        'hr_recruitment',
        'sign',
    ],
    'data': [
        'security/hr_contract_salary_security.xml',
        'security/ir.model.access.csv',

        'wizard/refuse_offer_wizard.xml',

        'views/hr_contract_salary_templates.xml',
        'views/hr_contract_views.xml',
        'views/hr_applicant_views.xml',
        'views/hr_candidate_views.xml',
        'views/hr_job_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_contract_salary_benefit_views.xml',
        'views/hr_contract_salary_personal_info_views.xml',
        'views/hr_contract_salary_resume_views.xml',
        'views/hr_contract_salary_offer_views.xml',
        'views/hr_contract_salary_offer_refusal_reason_views.xml',

        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/mail_templates.xml',
        'data/hr_contract_salary_benefits_data.xml',
        'data/hr_contract_salary_personal_info_data.xml',
        'data/hr_contract_salary_resume_data.xml',
        'data/hr_contract_salary_offer_refusal_reason_data.xml',

        'report/hr_contract_employee_report_views.xml',
        'report/hr_contract_history_report_views.xml',
    ],
    'demo': [
        'data/hr_contract_salary_demo.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_frontend': [
            'hr_contract_salary/static/src/scss/hr_contract_salary.scss',
            'hr_contract_salary/static/src/js/hr_contract_salary.js',
            'hr_contract_salary/static/src/xml/resume_sidebar.xml',
            'hr_contract_salary/static/src/xml/select_menu_wrapper_template.xml',
            'hr_contract_salary/static/src/xml/hr_contract_salary_select_menu_template.xml',
            'hr_contract_salary/static/src/js/hr_contract_salary_select_menu.js',
        ],
        'web.assets_backend': [
            'hr_contract_salary/static/src/js/binary_field_contract.js',
            'hr_contract_salary/static/src/xml/binary_field_contract.xml',
            'hr_contract_salary/static/src/js/url_field.js',
            'hr_contract_salary/static/src/xml/url_field.xml',
            'hr_contract_salary/static/src/js/copy_clipboard_field.js',
            'hr_contract_salary/static/src/scss/copy_clipboard_field.scss',
        ],
    }
}
