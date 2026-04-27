# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Luxembourg - Payroll',
    'countries': ['lu'],
    'category': 'Human Resources/Payroll',
    'depends': ['hr_payroll', 'hr_contract_reports', 'hr_work_entry_holidays', 'hr_payroll_holidays'],
    'auto_install': ['hr_payroll'],
    'version': '1.0',
    'description': """
Luxembourg Payroll Rules.
=========================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Integrated with Leaves Management
    """,
    'data': [
        'security/ir.model.access.csv',
        'data/rule_parameters/contributions_rules_data.xml',
        'data/rule_parameters/employer_rules_data.xml',
        'data/rule_parameters/general_rules_data.xml',
        'data/rule_parameters/tax_credit_rules_data.xml',
        'data/rule_parameters/withholding_taxes_rules_data.xml',
        'data/hr_work_entry_type_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_work_entry_data.xml',
        'views/hr_payroll_report.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/salary_rules/hr_salary_rule_data.xml',
        'data/salary_rules/hr_gratification_rule_data.xml',
        'data/salary_rules/hr_13th_month_rule_data.xml',
        'data/hr_holidays_data.xml',
        'data/hr_payroll_dashboard_warning_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payroll_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_payslip_templates.xml',
        'views/res_company.xml',
        'wizard/l10n_lu_monthly_declaration_wizard_views.xml',
    ],
    'demo': [
        'data/l10n_lu_hr_payroll_demo.xml',
    ],
    'license': 'OEEL-1',
}
