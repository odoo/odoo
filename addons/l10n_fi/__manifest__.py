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
    "name": "Finland - Accounting",
    "category": "Localization",
    "version": "1.0",
    "author": "RockIt Oy & Avoin.Systems",
    'description': """

This module for Finland localization
====================================

This module consists:

 - Tags supporting Finland Accounting

 """,
    "depends": [
        "account",
        "base_vat",
        "base_iban",
    ],
    "data": [
        "data/account_chart_template_data.xml",
        "data/account_account_template.xml",
        "data/account_account_tag_data.xml",
        "data/account_tax_template_data.xml",
        "data/account_fiscal_position_template_data.xml",
        "data/account_chart_template_configuration_data.xml",
    ],
}
