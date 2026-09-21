{
    "name": "DIN 5008",
    "version": "1.2",
    "category": "Accounting/Localizations",
    "description": "This is the base module that defines the DIN 5008 standard in Odoo.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "countries": [
        "de",
        "ch",
    ],
    "data": [
        "reports/din5008_base_document_layout.xml",
        "reports/din5008_report.xml",
        "reports/din5008_account_move_layout.xml",
        "data/report_layout.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "l10n_din5008/static/src/**/*",
        ],
    },
    "auto_install": True,
}
