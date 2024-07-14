# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Mongolia - Accounting Reports",
    'countries': ['mn'],
    "version" : "1.0",
    'category': 'Accounting/Localizations/Reporting',
    "author" : "BumanIT LLC, Odoo S.A",
    "description": """
Mongolian accounting reports.
====================================================
-Profit and Loss
-Balance Sheet
-Cash Flow Statement
-VAT Repayment Report
-Corporate Revenue Tax Report

Financial requirement contributor: Baskhuu Lodoikhuu. BumanIT LLC
""",
    "depends": ['l10n_mn', 'account_reports'],
    'data': [
        'data/balancesheet_report.xml',
        'data/cashflow_report.xml',
        'data/profit_and_loss_reports.xml',
        'data/tax_report.xml'
    ],
    'auto_install': ['l10n_mn', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
