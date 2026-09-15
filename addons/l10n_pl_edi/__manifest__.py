{
    "name": "Polish E-Invoicing FA(3)",
    "version": "1.2",
    "category": "Accounting/Localizations",
    "summary": "Support for FA(3) electronic invoices in Poland via KSeF",
    "description": "Export FA(3) compliant XML invoices and prepare for integration with KSeF.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "l10n_pl",
        "certificate",
    ],
    "external_dependencies": {
        "python": [
            "defusedxml",
        ],
    },
    "data": [
        "views/account_move_views.xml",
        "views/report_invoice.xml",
        "views/res_config_settings_views.xml",
        "data/ir_cron_data.xml",
        "data/fa3_template.xml",
    ],
    "demo": [
        "demo/account_invoice_demo.xml",
    ],
    "auto_install": [
        "l10n_pl",
    ],
}
