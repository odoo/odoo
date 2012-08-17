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
    'name': 'Budgets Management',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
This module allows accountants to manage analytic and crossovered budgets.
==========================================================================

Once the Budgets are defined (in Invoicing/Budgets/Budgets), the Project Managers 
can set the planned amount on each Analytic Account.

The accountant has the possibility to see the total of amount planned for each
Budget in order to ensure the total planned is not greater/lower than what he planned
for this Budget. Each list of record can also be switched to a graphical view of it.

Three reports are available:

    1. The first is available from a list of Budgets. It gives the spreading, for these Budgets, of the Analytic Accounts.

    2. The second is a summary of the previous one, it only gives the spreading, for the selected Budgets, of the Analytic Accounts.

    3. The last one is available from the Analytic Chart of Accounts. It gives the spreading, for the selected Analytic Accounts of Budgets.
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/budget.jpeg','images/budgetary_position.jpeg'],
    'depends': ['account'],
    'data': [],
    'data': [
        'security/ir.model.access.csv',
        'security/account_budget_security.xml',
        'account_budget_view.xml',
        'account_budget_report.xml',
        'account_budget_workflow.xml',
        'wizard/account_budget_analytic_view.xml',
        'wizard/account_budget_report_view.xml',
        'wizard/account_budget_crossovered_summary_report_view.xml',
        'wizard/account_budget_crossovered_report_view.xml',
    ],
    'demo': ['account_budget_demo.xml'],
    'test':[
            'test/account_budget.yml',
            'test/account_budget_report.yml',
            ],
    'installable': True,
    'auto_install': False,
    'certificate': '0043819694157',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
