# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Sweden - Accounting",
    "version": "1.0",
    "author": "XCLUDE, Odoo SA",
    "category": "Accounting/Localizations/Account Charts",
    'description': """
Swedish Accounting
------------------

This is the base module to manage the accounting chart for Sweden in Odoo.
It also includes the invoice OCR payment reference handling.
    """,
    "depends": ["account", "base_vat"],
    "data": [
        'data/account.account.tag.csv',
        "data/account_chart_template_before_accounts.xml",
        "data/account.account.template-K3.csv",
        "data/account.account.template-K2.csv",
        "data/account.account.template.csv",
        "data/account_chart_template_after_accounts.xml",
        "data/account_tax_group_data.xml",
        "data/account_tax_report_data.xml",
        "data/account_tax_template.xml",
        "data/account_fiscal_position_template.xml",
        "data/account_fiscal_position_account_template.xml",
        "data/account_fiscal_position_tax_template.xml",
        "data/account_chart_template_configuration.xml",
        "views/partner_view.xml",
        "views/account_journal_view.xml",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
 }
