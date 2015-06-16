# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Invoice on Timesheets',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Generate your Invoices from Expenses, Timesheet Entries.
========================================================

Module to generate invoices based on costs (human resources, expenses, ...).

You can define price lists in analytic account, make some theoretical revenue
reports.""",
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/employees',
    'images': ['images/hr_bill_task_work.jpeg','images/hr_type_of_invoicing.jpeg'],
    'depends': ['hr_timesheet', 'report'],
    'data': [
        'security/ir.model.access.csv',
        'hr_timesheet_invoice_data.xml',
        'hr_timesheet_invoice_view.xml',
        'hr_timesheet_invoice_wizard.xml',
        'hr_timesheet_invoice_report.xml',
        'report/report_analytic_view.xml',
        'report/hr_timesheet_invoice_report_view.xml',
        'wizard/hr_timesheet_analytic_profit_view.xml',
        'wizard/hr_timesheet_invoice_create_view.xml',
        'wizard/hr_timesheet_invoice_create_final_view.xml',
        'views/report_analyticprofit.xml',
    ],
    'demo': ['hr_timesheet_invoice_demo.xml'],
    'test': ['../account/test/account_minimal_test.xml',
             'test/test_hr_timesheet_invoice.yml',
             'test/test_hr_timesheet_invoice_no_prod_tax.yml',
             'test/hr_timesheet_invoice_report.yml',
    ],
    'installable': True,
    'auto_install': False,
}
