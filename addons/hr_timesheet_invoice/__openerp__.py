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
    'name': 'Invoice on analytic lines',
    'version': '1.0',
    'category': 'Generic Modules/Accounting',
    'description': """
Module to generate invoices based on costs (human resources, expenses, ...).
============================================================================
You can define price lists in analytic account, make some theoretical revenue
reports, eso.""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/hr_bill_task_work.jpeg','images/hr_type_of_invoicing.jpeg'],
    'depends': ['account', 'hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'hr_timesheet_invoice_data.xml',
        'hr_timesheet_invoice_view.xml',
        'hr_timesheet_invoice_wizard.xml',
        'hr_timesheet_invoice_report.xml',
        'report/report_analytic_view.xml',
        'report/hr_timesheet_invoice_report_view.xml',
        'wizard/hr_timesheet_invoice_analytic_cost_ledger_view.xml',
        'wizard/hr_timesheet_analytic_profit_view.xml',
        'wizard/hr_timesheet_invoice_create_view.xml',
        'wizard/hr_timesheet_invoice_create_final_view.xml',
        'board_hr_timesheet_invoice.xml',
    ],
    'demo': [
        'hr_timesheet_invoice_demo.xml',
    ],
    'test': ['test/test_hr_timesheet_invoice.yml',
             'test/hr_timesheet_invoice_report.yml',
             ],
    'installable': True,
    'active': False,
    'certificate': '0056091842381',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
