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
        'security/hr_security.xml',
        'wizard/hr_payroll_payslips_by_employees.xml',
        'hr_payroll_view.xml',
        'hr_payroll_workflow.xml',
        'hr_payroll_sequence.xml',
        'hr_payroll_report.xml',
        'hr_payroll_data.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payroll_contribution_register_report.xml',
        'res_config_view.xml',
        'views/report_contributionregister.xml',
        'views/report_payslip.xml',
        'views/report_payslipdetails.xml',
    ],
    'test': [
        'test/payslip.yml',
    ],
    'demo': ['hr_payroll_demo.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
