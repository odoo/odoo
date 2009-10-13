# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Human Resources Expenses Tracking',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
    This module aims to manage employee's expenses.

    The whole workflow is implemented:
    * Draft expense
    * Confirmation of the sheet by the employee
    * Validation by his manager
    * Validation by the accountant and invoice creation
    * Payment of the invoice to the employee

    This module also use the analytic accounting and is compatible with
    the invoice on timesheet module so that you will be able to automatically
    re-invoice your customer's expenses if your work by project.
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['hr', 'account', 'account_tax_include'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'hr_expense_sequence.xml',
        'hr_expense_workflow.xml',
        'hr_expense_view.xml',
        'hr_expense_report.xml',
        'process/hr_expense_process.xml'
    ],
    'demo_xml': ['hr.expense.expense.csv'],
    'installable': True,
    'active': False,
    'certificate': '0062479841789',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
