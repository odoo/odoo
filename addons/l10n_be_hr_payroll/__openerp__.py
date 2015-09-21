# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgium - Payroll',
    'category': 'Localization',
    'depends': ['hr_payroll'],
    'version': '1.0',
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

    'auto_install': False,
    'demo': ['l10n_be_hr_payroll_demo.xml'],
    'website': 'https://www.odoo.com/page/accounting',
    'data':[
        'l10n_be_hr_payroll_view.xml',
        'l10n_be_hr_payroll_data.xml',
        'data/hr.salary.rule.csv',
    ],
    'installable': True
}
