# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll',
    'category': 'Localization',
    'depends': ['hr_payroll'],
    'description': """
Belgian Payroll Rules.
======================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Holiday Management
    * Salary Maj, ONSS, Withholding Tax, Child Allowance, ...
    """,

    'demo': ['data/l10n_be_hr_payroll_demo.xml'],
    'website': 'https://www.odoo.com/page/accounting',
    'data':[
        'views/l10n_be_hr_payroll_view.xml',
        'data/l10n_be_hr_payroll_data.xml',
        'data/hr.salary.rule.csv',
    ],
}
