{
    "name": "Romania - E-invoicing",
    "version": "1.1",
    "category": "Accounting/Localizations/EDI",
    "summary": "E-Invoice implementation for Romania",
    "description": """
E-invoice implementation for Romania
    """,
    "author": "Odoo",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "account_edi_ubl_cii",
        "l10n_ro",
    ],
    "data": [
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_ro_edi/static/src/components/*",
        ],
    },
    "auto_install": True,
    "uninstall_hook": "uninstall_hook",
}
