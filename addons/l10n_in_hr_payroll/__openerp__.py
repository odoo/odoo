# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indian Payroll',
    'category': 'Localization',
    'depends': ['hr_payroll'],
    'version': '1.0',
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
    * Integrated with Holiday Management
    * Medical Allowance, Travel Allowance, Child Allowance, ...
    - Payroll Advice and Report
    - Yearly Salary by Head and Yearly Salary by Employee Report
    """,
    'active': False,
    'data': [
         'l10n_in_hr_payroll_view.xml',
         'data/l10n_in_hr_payroll_data.xml',
         'data/hr.salary.rule.csv',
         'security/ir.model.access.csv',
         'l10n_in_hr_payroll_report.xml',
         'l10n_in_hr_payroll_sequence.xml',
         'views/report_payslipdetails.xml',
         'views/report_hrsalarybymonth.xml',
         'wizard/hr_salary_employee_bymonth_view.xml',
         'wizard/hr_yearly_salary_detail_view.xml',
         'report/payment_advice_report_view.xml',
         'report/payslip_report_view.xml',
         'views/report_hryearlysalary.xml',
         'views/report_payrolladvice.xml',
     ],
    'test': [
        'test/payment_advice.yml',
        'test/payment_advice_batch.yml'
    ],

    'demo': ['l10n_in_hr_payroll_demo.xml'],
    'installable': True
}
