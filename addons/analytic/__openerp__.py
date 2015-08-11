# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Analytic Accounting',
    'version': '1.1',
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
    'test': [
        'test/analytic_hierarchy.yml',
    ],
    'installable': True,
    'auto_install': False,
}
