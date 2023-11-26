# Part of Odoo. See LICENSE file for full copyright and licensing details.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# Copyright (C) 2022 Fadoo  (<http://www.Fadoo.ir>).

{
    "name": "Iran - Accounting",
    "version": "1.0",
    "category": "Accounting/Localizations/Account Charts",
    "summary": """
Iran Accounting Module
============================
iran accounting chart and localization.

Also:
    - activates a number of regional currencies.
    - sets up Iran taxes.
    """,
    "author": "Fadoo, Odoo Community Association (OCA)",
    "maintainer": ["saeed-raesi"],
    "license": "AGPL-3",
    "website": "https://github.com/OCA/l10n-iran",
    "depends": [
        "account",
        "base_vat",
        "l10n_multilang",
    ],
    "data": [
        "data/l10n_ir_chart_data.xml",
        "data/account.group.template.csv",
        "data/account.account.template.csv",
        "data/account_tax_group_data.xml",
        "data/account_tax_report_data.xml",
        "data/account_tax_template_data.xml",
        "data/l10n_ir_chart_post_data.xml",
        "data/account_fiscal_position_data.xml",
        "data/account_chart_template_data.xml",
        "data/res_currency_data.xml",
        "data/res.bank.csv",
    ],
}
