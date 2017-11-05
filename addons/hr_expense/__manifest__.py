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
    'depends': ['hr_contract', 'account', 'web_tour'],
    'data': [
        'security/hr_expense_security.xml',
        'security/ir.model.access.csv',
        'data/hr_expense_data.xml',
        'data/hr_expense_sequence.xml',
        'wizard/hr_expense_refuse_reason_views.xml',
        'wizard/hr_expense_sheet_register_payment.xml',
        'views/hr_expense_views.xml',
        'security/ir_rule.xml',
        'report/report_expense_sheet.xml',
        'views/hr_dashboard.xml',
        'views/hr_expense.xml',
        'views/res_config_settings_views.xml',
        'data/web_planner_data.xml',
    ],
    'demo': ['data/hr_expense_demo.xml'],
    'installable': True,
    'application': True,
}
