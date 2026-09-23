{
    "name": "Kenya Tremol Device EDI Integration",
    "version": "1.1",
    "category": "Accounting/Localizations/EDI",
    "summary": "Kenya Tremol Device EDI Integration",
    "description": """
This module integrates with the Kenyan G03 Tremol control unit device to the KRA through TIMS.
    """,
    "author": "Odoo",
    "license": "LGPL-3",
    "depends": [
        "l10n_ke",
    ],
    "countries": [
        "ke",
    ],
    "data": [
        "security/ir.access.csv",
        "views/account_move_view.xml",
        "views/report_invoice.xml",
        "views/res_config_settings_view.xml",
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_ke_edi_tremol/static/src/components/*",
        ],
    },
}
