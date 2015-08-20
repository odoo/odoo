# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Expense Tracker',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 95,
    'summary': 'Expenses Validation, Invoicing',
    'description': """
Manage expenses by Employees
============================

This application allows you to manage your employees' daily expenses. It gives you access to your employees’ fee notes and give you the right to complete and validate or refuse the notes. After validation it creates an invoice for the employee.
Employee can encode their own expenses and the validation flow puts it automatically in the accounting after validation by managers.


The whole flow is implemented as:
---------------------------------
* Draft expense
* Confirmation of the sheet by the employee
* Validation by his manager
* Validation by the accountant and accounting entries creation

This module also uses analytic accounting and is compatible with the invoice on timesheet module so that you are able to automatically re-invoice your customers' expenses if your work by project.
    """,
    'website': 'https://www.odoo.com/page/expenses',
    'depends': ['hr', 'account_accountant', 'report'],
    'data': [
        'security/ir.model.access.csv',
        'hr_expense_data.xml',
        'hr_expense_sequence.xml',
        'hr_expense_workflow.xml',
        'hr_expense_view.xml',
        'hr_expense_report.xml',
        'security/ir_rule.xml',
        'report/hr_expense_report_view.xml',
        'hr_expense_installer_view.xml',
        'views/report_expense.xml',
        'hr_dashboard.xml',
    ],
    'demo': ['hr_expense_demo.xml'],
    'test': [
        '../account/test/account_minimal_test.xml',
        'test/expense_demo.yml',
        'test/expense_process.yml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
