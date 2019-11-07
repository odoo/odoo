# -*- coding: utf-8 -*-
{
    "name": "Swedish - Accounting",
    "version": "12.0.0.1",    
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
        "data/account_tax_template.xml",
        "data/account_fiscal_position_template.xml",        
        "data/account_fiscal_position_tax_template.xml",
        "data/account_chart_template_configure.xml",
    ],
    "active": False
}