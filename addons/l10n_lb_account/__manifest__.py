{
    "name": "Lebanon - Accounting",
    "countries": ["lb"],
    "version": "1.0",
    "description": """
This is the base module to manage the accounting chart for Lebanon in Odoo.
==============================================================================
Lebanon accounting basic charts,taxes and localization.
Activates:
* Chart of Accounts
* Taxes
* Fiscal Positions
    """,
    "category": "Accounting/Localizations/Account Charts",
    "depends": ["account"],
    "data": [
        "data/res.country.state.csv",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "license": "LGPL-3",
}
