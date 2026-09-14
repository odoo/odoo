{
    "name": "Serbia - eFaktura E-invoicing",
    "version": "1.1",
    "category": "Accounting/Localizations/EDI",
    "summary": "E-Invoice implementation for Serbia",
    "description": """
eFaktura E-invoice implementation for Serbia
    """,
    "author": "Odoo",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "account_edi_ubl_cii",
        "l10n_rs",
    ],
    "countries": [
        "rs",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/account_move.xml",
        "views/res_partner_views.xml",
    ],
    "auto_install": True,
}
