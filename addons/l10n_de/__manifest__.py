{
    "name": "Germany - Accounting",
    "version": "3.1",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
Dieses  Modul beinhaltet einen deutschen Kontenrahmen basierend auf dem SKR03 oder SKR04.
=========================================================================================

German accounting chart and localization.
By default, the audit trail is enabled for GoBD compliance.
    """,
    "author": "openbig.org (http://www.openbig.org)",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/germany.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account_iban",
        "account_vat",
        "l10n_din5008",
        "account",
        "account_edi_ubl_cii",
    ],
    "external_dependencies": {
        "python": [
            "python-stdnum",
        ],
        "apt": {
            "python-stdnum": "python3-stdnum",
        },
    },
    "countries": [
        "de",
    ],
    "data": [
        "security/ir.access.csv",
        "data/account_account_tags_data.xml",
        "views/account_view.xml",
        "views/res_company_views.xml",
        "wizards/account_secure_entries_wizard.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": [
        "account",
    ],
    "post_init_hook": "_post_init_hook",
}
