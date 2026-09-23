{
    "name": "Czech - Accounting",
    "version": "1.2",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
Czech accounting chart and localization.  With Chart of Accounts with taxes and basic fiscal positions.

Tento modul definuje:

- Českou účetní osnovu za rok 2020

- Základní sazby pro DPH z prodeje a nákupu

- Základní fiskální pozice pro českou legislativu
    """,
    "author": "26HOUSE (http://www.26house.com)",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_edi_ubl_cii",
        "account_iban",
        "account_vat",
    ],
    "countries": [
        "cz",
    ],
    "data": [
        "data/tax_report.xml",
        "data/l10n_cz.tax_office.csv",
        "views/report_invoice.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/report_template.xml",
        "views/tax_office_view.xml",
        "security/ir.access.csv",
        "views/l10n_cz_menus.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": [
        "account",
    ],
}
