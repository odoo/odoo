{
    "name": "Gulf Cooperation Council - Invoice",
    "version": "1.0.2",
    "category": "Accounting/Localizations",
    "description": """
Adds Arabic as a secondary language on your invoice, credit note, debit note, vendor bill, and refund bill
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.access.csv",
        "views/report_invoice.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "l10n_gcc_invoice/static/src/scss/styles.scss",
        ],
    },
    "post_init_hook": "_l10n_gcc_invoice_post_init",
}
