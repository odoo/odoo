#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payroll',
    'category': 'Human Resources',
    'sequence': 38,
    'summary': 'Manage your employee payroll records',
    'description': """
Generic Payroll system.
=======================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Holiday Management
    """,
    'website': 'https://www.odoo.com/page/employees',
    'depends': [
        'hr_contract',
        'hr_holidays',
        'decimal_precision',
        'report',
    ],
    'data': [
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_employee_views.xml',
        'data/hr_payroll_sequence.xml',
        'views/hr_payroll_report.xml',
        'data/hr_payroll_data.xml',
        'wizard/hr_payroll_contribution_register_report_views.xml',
        'views/hr_payroll_config_settings_views.xml',
        'views/report_contributionregister_templates.xml',
        'views/report_payslip_templates.xml',
        'views/report_payslipdetails_templates.xml',
    ],
    'demo': ['data/hr_payroll_demo.xml'],
}
