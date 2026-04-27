# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mexico - Payroll',
    'countries': ['mx'],
    'category': 'Human Resources/Payroll',
    'depends': ['hr_payroll', 'hr_contract_reports', 'hr_work_entry_holidays', 'hr_payroll_holidays'],
    'auto_install': ['hr_payroll'],
    'version': '1.0',
    'description': """
Mexican Payroll Rules.
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
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'views/hr_payroll_report.xml',
        'data/hr_work_entry_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_rule_parameters_data.xml',
        'data/hr_holiday_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/salary_rules/hr_salary_rule_regular_pay_data.xml',
        'data/salary_rules/hr_salary_rule_christmas_bonus_data.xml',
        'views/report_payslip_templates.xml',
        'views/hr_contract_views.xml',
    ],
    'demo': [
        'data/l10n_mx_hr_payroll_demo.xml',
    ],
    'license': 'OEEL-1',
}
