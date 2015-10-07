#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payroll',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 38,
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
        'hr',
        'hr_contract',
        'hr_holidays',
        'decimal_precision',
        'report',
    ],
    'data': [
        'data/hr_payroll_data.xml',
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payslip_employees_views.xml',
        'wizard/payslip_lines_contribution_register_views.xml',
        'views/hr_payroll_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contribution_register_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payroll_workflow.xml',
        'views/hr_payroll_sequence.xml',
        'views/hr_payroll_report.xml',
        'views/res_config_views.xml',
        'views/contributionregister_templates.xml',
        'views/payslip_templates.xml',
        'views/payslipdetails_templates.xml',
    ],
    'test': [
        'test/payslip.yml',
    ],
    'demo': ['data/hr_payroll_demo.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
