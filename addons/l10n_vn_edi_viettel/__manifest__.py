{
    "name": "Vietnam - E-invoicing",
    "version": "1.1",
    "category": "Accounting/Localizations/EDI",
    "summary": "E-invoicing using SInvoice by Viettel",
    "description": """
Vietnam - E-invoicing
=====================
Using SInvoice by Viettel
    """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/vietnam.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "l10n_vn",
    ],
    "countries": [
        "vn",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/sinvoice_views.xml",
        "wizards/account_move_reversal_view.xml",
        "wizards/l10n_vn_edi_cancellation_request_views.xml",
        "views/l10n_vn_edi_viettel_menus.xml",
    ],
    "uninstall_hook": "uninstall_hook",
}
