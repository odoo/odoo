# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Expense Management',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 29,
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
* Validation by the accountant and receipt creation

This module also uses analytic accounting and is compatible with the invoice on timesheet module so that you are able to automatically re-invoice your customers' expenses if your work by project.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/hr_expenses_analysis.jpeg', 'images/hr_expenses.jpeg'],
    'depends': ['hr', 'account_voucher', 'account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'hr_expense_data.xml',
        'hr_expense_sequence.xml',
        'hr_expense_workflow.xml',
        'hr_expense_view.xml',
        'hr_expense_report.xml',
        'process/hr_expense_process.xml',
        'security/ir_rule.xml',
        'report/hr_expense_report_view.xml',
        'board_hr_expense_view.xml',
        'hr_expense_installer_view.xml',
    ],
    'demo': ['hr_expense_demo.xml'],
    'test': [
        'test/expense_demo.yml',
        'test/expense_process.yml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
