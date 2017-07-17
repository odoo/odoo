# coding=utf-8
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
    "version": "1.0.0",
    "author": "RockIt Oy & Avoin.Systems",
    "depends": [
        "l10n_fi",
    ],
    "data": [
        "data/account_chart_template_pre_data.xml",  # 1st
        "data/account_account_template_data.xml",
        "data/account_tax_template_data.xml",
        "data/account_fiscal_position_template_data.xml",
        "data/account_chart_template_post_data.xml",  # 2nd last
        "data/account_chart_template_data.yml",  # Load / evaluate this last
    ],
}
