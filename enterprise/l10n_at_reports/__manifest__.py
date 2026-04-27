# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2015 WT-IO-IT GmbH (https://www.wt-io-it.at)
#                    Mag. Wolfgang Taferner <wolfgang.taferner@wt-io-it.at>

{
    "name": "Austria - Accounting Reports",
    "version": "2.0",
    "author": "WT-IO-IT GmbH, Wolfgang Taferner",
    "website": "https://www.wt-io-it.at",
    "license": 'OEEL-1',
    "category": "Accounting/Localizations/Reporting",
    'summary': "Austrian Financial Reports",
    'description': """

Accounting reports for Austria.
================================

    * Defines the following reports:
        * Profit/Loss (§ 231 UGB Gesamtkostenverfahren)
        * Balance Sheet (§ 224 UGB)

    """,
    "depends": [
        'l10n_at',
        'account_reports',
        'account_accountant',
    ],
    "data": [
        'data/account_financial_html_report_profit_loss.xml',
        'data/account_financial_html_report_balance.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_at', 'account_reports'],
}
