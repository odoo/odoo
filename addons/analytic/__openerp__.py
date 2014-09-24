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
    'name' : 'Analytic Accounting',
    'version': '1.1',
    'author' : 'OpenERP SA',
    'website' : 'https://www.odoo.com/page/accounting',
    'category': 'Hidden/Dependency',
    'depends' : ['base', 'decimal_precision', 'mail'],
    'description': """
Module for defining analytic accounting object.
===============================================

In OpenERP, analytic accounts are linked to general accounts but are treated
totally independently. So, you can enter various different analytic operations
that have no counterpart in the general financial accounts.
    """,
    'data': [
        'security/analytic_security.xml',
        'security/ir.model.access.csv',
        'data/analytic_sequence.xml',
        'views/analytic_view.xml',
        'data/analytic_data.xml',
        'analytic_report.xml',
        'wizard/account_analytic_balance_report_view.xml',
        'wizard/account_analytic_cost_ledger_view.xml',
        'wizard/account_analytic_inverted_balance_report.xml',
        'wizard/account_analytic_journal_report_view.xml',
        'wizard/account_analytic_cost_ledger_for_journal_report_view.xml',
        'wizard/account_analytic_chart_view.xml',
        'views/report_analyticbalance.xml',
        'views/report_analyticjournal.xml',
        'views/report_analyticcostledgerquantity.xml',
        'views/report_analyticcostledger.xml',
        'views/report_invertedanalyticbalance.xml',
    ],
    'demo': [
        'data/analytic_demo.xml',
        'data/analytic_account_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
