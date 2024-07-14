# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Morocco - Payroll',
    'countries': ['ma'],
    'category': 'Human Resources/Payroll',
    'depends': ['hr_payroll', 'l10n_ma'],
    'version': '1.0',
    'description': """
Morocco Payroll Rules.
=========================

    * Employee Details
    * Employee Contracts
    """,
    'data': [
        'data/hr_contract_type_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/res_partner_data.xml',
        'data/hr_rule_parameters_data.xml',
        'data/hr_salary_rule_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_payslip_templates.xml',
    ],
    'demo': [
        'data/l10n_ma_hr_payroll_demo.xml',
    ],
    'license': 'OEEL-1',
}
