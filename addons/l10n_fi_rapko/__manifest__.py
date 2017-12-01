# -*- coding: utf-8 -*-
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
    "author": "RockIt Oy & Avoin.Systems",
    'description': """

Base module for Finland localization
====================================

This module consists:

 - Generic Finland chart of accounts
 - Finland Taxes
 - Finland Fiscal position
 """,
    "depends": [
        "l10n_fi",
    ],
    "data": [
        "data/account_chart_template_data.xml",
        "data/l10n_fi_rapko_chart_data.xml",
        "data/account_tax_template_data.xml",
        "data/account_fiscal_position_template_data.xml",
        "data/account_chart_template_configuration_data.xml",
    ],
    "auto_install": True,
}
