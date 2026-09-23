{
    "name": "Netherlands - Accounting",
    "version": "3.5",
    "category": "Accounting/Localizations/Account Charts",
    "author": "Onestein (http://www.onestein.eu)",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/netherlands.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account_iban",
        "account_vat",
        "account",
        "account_edi_ubl_cii",
    ],
    "countries": [
        "nl",
    ],
    "data": [
        "security/ir.access.csv",
        "data/account_account_tag.xml",
        "data/account_tax_report_data.xml",
        "data/res_country_group.xml",
        "views/res_config_settings_view.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": [
        "account",
    ],
}
