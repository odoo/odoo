{
    "name": "Georgia - Electronic Invoicing",
    "countries": ["ge"],
    "category": "Accounting/Localizations/EDI",
    "summary": "E-Invoicing with RS.ge, Georgia's Revenue Service",
    "description": """
Electronic invoicing for Georgia, through direct integration with RS.ge (Georgia's Revenue
Service):

- Configure RS.ge service-user credentials from Accounting Settings
- Resolve a customer's tax identification number to their RS.ge identifier
- Register sales invoices with RS.ge and retrieve the official F-series/F-number
- Synchronise the RS.ge status of an invoice, on demand or for a whole journal
- Correct a registered invoice: cancel the transaction, modify it, or refund it
- Request the cancellation of a registered invoice, and mirror it once the customer accepts
    """,
    "depends": ["l10n_ge", "account"],
    "data": [
        "security/ir.access.csv",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "wizard/l10n_ge_edi_k_invoice_wizard_views.xml",
    ],
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
