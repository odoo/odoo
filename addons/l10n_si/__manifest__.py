# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Slovenian - Accounting",
    "version": "1.1",
    "author": "Odoo S.A.",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
        Chart of accounts and taxes for Slovenia.
    """,
    "depends": [
        "account",
        "base_vat",
        "l10n_multilang"
    ],
    "data": [
        "data/l10n_si_chart_data.xml",
        "data/account.account.template.csv",
        "data/account.group.template.csv",
        "data/account_tax_group.xml",
        "data/account_tax_report_data.xml",
        "data/account_tax_data.xml",
        "data/account_fiscal_position_template.xml",
        "data/account_fiscal_position_account_template.xml",
        "data/account_fiscal_position_tax_template.xml",
        "data/account_chart_template_configure_data.xml",
        "data/account_chart_template_data.xml",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
    'license': 'LGPL-3',
}
