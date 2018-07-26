# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Expense Tracker',
    'version': '2.0',
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
* Submitted by the employee to his manager
* Approved by his manager
* Validation by the accountant and accounting entries creation

This module also uses analytic accounting and is compatible with the invoice on timesheet module so that you are able to automatically re-invoice your customers' expenses if your work by project.
    """,
    'website': 'https://www.odoo.com/page/expenses',
    'depends': ['hr_contract', 'account_accountant', 'report'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_expense_data.xml',
        'data/hr_expense_sequence.xml',
        'wizard/hr_expense_refuse_reason.xml',
        'views/hr_expense_views.xml',
        'security/ir_rule.xml',
        'views/hr_expense_installer_views.xml',
        'views/report_expense.xml',
        'data/web_tip_data.xml',
        'views/hr_dashboard.xml',
    ],
    'demo': ['data/hr_expense_demo.xml'],
    'installable': True,
    'application': True,
}
