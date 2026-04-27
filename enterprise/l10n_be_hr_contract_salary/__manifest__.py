# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator (Belgium)',
    'category': 'Human Resources',
    'summary': 'Salary Package Configurator',
    'depends': [
        'hr_contract_salary_payroll',
        'l10n_be_hr_payroll_fleet',
    ],
    'data': [
        'data/hr_contract_salary_benefit_data.xml',
        'data/hr_contract_salary_resume_data.xml',
        'data/hr_contract_salary_personal_info_data.xml',
        'data/cp200/employee_termination_fees_data.xml',
        'data/hr_payroll_dashboard_warning_data.xml',

        'report/hr_contract_history_report_views.xml',

        'views/hr_contract_views.xml',
        'views/hr_job_views.xml',
        'views/hr_payroll_menu.xml',
        'views/res_config_settings_views.xml',
        'views/hr_contract_salary_template.xml',
        'views/hr_contract_salary_offer_views.xml',
        'views/hr_fleet_state_views.xml',
    ],
    'demo': [
        'data/l10n_be_hr_contract_salary_demo.xml',
        # 'data/hr_contract_salary_benefit_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'l10n_be_hr_contract_salary/static/src/**/*',
        ],
    }
}
