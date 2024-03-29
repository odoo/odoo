# -*- coding: utf-8 -*-

{
    "name": "Uganda - Accounting",
    "countries": ["ug"],
    "version": "1.0.0",
    "category": "Accounting/Localizations/Account Charts",
    "license": "LGPL-3",
    "description": """
This is the basic Ugandian localisation necessary to run Odoo in UG:
================================================================================
    - Chart of accounts
    - Taxes
    - Fiscal positions
    - Default settings
    - Tax report
    """,
    "depends": [
        "account",
    ],
    "data": [
        "data/account_tax_report_data.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ]
}
