# -*- coding: utf-8 -*-
{
    "name": "Swedish - Accounting",
    "version": "1.0",    
    "description": """This is the minimum accounting chart BAS 2019, for Swedish K2 companies.""",
    "author": "XCLUDE",
    "website": "https://www.xclude.se",
    "category": "Localization",
    "depends": [
        "account",
        "base_vat",
        "base_iban",
    ],
    "data": [
        "data/account_account_template.xml",
        "data/account_tax_group_template.xml",       
        "data/account_tax_template.xml",
        "data/account_fiscal_position_template.xml",
        "data/account_fiscal_position_tax_template.xml",
        "data/account_fiscal_position_account_template.xml",
        "data/account_chart_template_configure.xml",
        "data/res.bank.csv",
        "views/res_partner_views.xml",
    ],
    "active": False
}