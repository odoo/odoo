# coding=utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Avoin.Systems 2016
# Authors:
#   Miku Laitinen (Avoin.Systems)
#   Mikko Närjänen (Avoin.Systems)
#   Toni Pesola (Avoin.Systems)

# noinspection PyStatementEffect
{
    "name": "Finnish localization",
    "version": "1.0",
    "category": "Localization",
    "description": """
        General modifications useful to any Finnish company.
    """,
    "author": "Avoin.Systems",
    "depends": [
        "account",
    ],
    "data": [
        "views/res_config.xml",
        "views/res_partner.xml",
        "views/account_invoice.xml",
    ],
    "installable": True,
}
