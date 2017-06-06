# coding=utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) RockIT Oy 2014-
# Copyright (C) Avoin.Systems 2014-
# Authors:
#   Miku Laitinen (Avoin.Systems)
#   Mikko Närjänen (Avoin.Systems)
#   Toni Pesola (Avoin.Systems)
#   Mikko Salmela (RockIT Oy)

# noinspection PyStatementEffect
{
    "name": "Finland - Accounting (Raportointikoodisto)",
    "category": "Localization",
    "version": "1.0.0",
    "description": """
    Finnish chart of accounts, value added taxes and useful new fields.

    Standard Business Reporting (=SBR or Raportointikoodisto) is a standard code set
    making Finnish official reporting easier by supplementing the common chart of accounts.

    Raportointikoodisto details: http://www.raportointikoodisto.fi/

    Finnish regulations for accounting: http://www.finlex.fi/fi/laki/ajantasa/1997/19971339
    """,
    "author": "RockIt Oy & Avoin.Systems",
    "depends": [
        "account",
    ],
    "data": [
        "data/account_chart_template_pre.xml",  # 1st
        "data/accounts.xml",
        "data/tax_tags.xml",
        "data/taxes.xml",
        "data/fiscal_positions.xml",
        "data/account_chart_template_post.xml",  # 2nd last
        "data/account_chart_template.yml",  # Load / evaluate this last
        "views/account_invoice.xml",
        "views/res_config.xml",
        "views/res_partner.xml",
    ],
    "installable": True,
}
