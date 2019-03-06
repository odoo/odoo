# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian Payroll',
    'category': 'Human  Resources',
    'depends': ['hr_payroll'],
    'description': """
Indian Payroll Salary Rules.
============================

    -Configuration of hr_payroll for India localization
    -All main contributions rules for India payslip.
    * New payslip report
    * Employee Contracts
    * Allow to configure Basic / Gross / Net Salary
    * Employee PaySlip
    * Allowance / Deduction
    * Integrated with Leaves Management
    * Medical Allowance, Travel Allowance, Child Allowance, ...
    - Payroll Advice and Report
    - Yearly Salary by Head and Yearly Salary by Employee Report
    """,
    'data': [
         'views/l10n_in_hr_payroll_view.xml',
         'data/l10n_in_hr_payroll_data.xml',
         'data/hr.salary.rule.csv',
         'security/ir.model.access.csv',
         'views/l10n_in_hr_payroll_report.xml',
         'data/l10n_in_hr_payroll_sequence_data.xml',
         'views/report_payslip_details_template.xml',
         'views/report_hr_salary_employee_bymonth_template.xml',
         'wizard/hr_salary_employee_bymonth_view.xml',
         'wizard/hr_yearly_salary_detail_view.xml',
         'report/payment_advice_report_view.xml',
         'report/payslip_report_view.xml',
         'views/report_hr_yearly_salary_detail_template.xml',
         'views/report_payroll_advice_template.xml',
     ],
    'demo': ['demo/l10n_in_hr_payroll_demo.xml'],
}
