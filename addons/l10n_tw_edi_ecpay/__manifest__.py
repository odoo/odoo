{
    "name": "Taiwan - E-invoicing",
    "version": "1.1",
    "category": "Accounting/Localizations/EDI",
    "summary": "E-invoicing using ECpay",
    "description": """
        Taiwan - E-invoicing
        =====================
        This module allows the user to send their invoices to the Ecpay system.
    """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "l10n_tw",
        "account_vat",
        "integration",
    ],
    "countries": [
        "tw",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_setting_view.xml",
        "views/account_tax.xml",
        "views/account_move_view.xml",
        "views/account_move_reversal_view.xml",
        "views/l10n_tw_edi_invoice_cancel_view.xml",
        "views/l10n_tw_edi_invoice_print_view.xml",
    ],
    "uninstall_hook": "uninstall_hook",
}
