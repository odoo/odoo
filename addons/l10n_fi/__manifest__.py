# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) RockIT Oy 2014-
# Copyright (C) Avoin.Systems 2014-
# Authors:
#   Miku Laitinen (Avoin.Systems)
#   Mikko Närjänen (Avoin.Systems)
#   Toni Pesola (Avoin.Systems)
#   Mikko Salmela (RockIT Oy)

{
    "name": "Finland - Accounting (Raportointikoodisto)",
    "category": "Localization",
    "version": "1.0",
    "description": """
    Finnish chart of accounts, value added taxes and useful new fields.

    Standard Business Reporting (=SBR or Raportointikoodisto) is a standard code set
    making Finnish official reporting easier by supplementing the common chart of accounts.

    Raportointikoodisto details: http://www.raportointikoodisto.fi/

    Finnish regulations for accounting: http://www.finlex.fi/fi/laki/ajantasa/1997/19971339
    """,
    "author": "RockIt Oy & Avoin.Systems",
    "website": 'https://avoin.systems',
    "depends": [
        "account",
        "base_iban",
        "base_vat",
    ],
    "data": [
        "data/l10n_fi_chart_data.xml",  # 1st
        "data/account_account_template_data.xml",
        "data/account_account_tag_data.xml",
        "data/account_tax_template_data.xml",
        "data/account_fiscal_position_template_data.xml",
        "data/account_chart_template_data.xml",  # 2nd last
        "data/account_chart_template_configure_data.xml",  # Load / evaluate this last
    ],
    "installable": True,
}
