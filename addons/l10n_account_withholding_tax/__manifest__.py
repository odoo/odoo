{
    "name": "Withholding Tax on Payment",
    "version": "1.1",
    "category": "Accounting/Localizations",
    "description": "Allows to register withholding taxes during the payment of an invoice or bill.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.access.csv",
        "views/account_payment_views.xml",
        "views/account_tax_views.xml",
        "views/report_payment_receipt_templates.xml",
        "views/res_config_settings.xml",
        "wizards/account_payment_register_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_account_withholding_tax/static/src/helpers/*.js",
        ],
        "web.assets_frontend": [
            "l10n_account_withholding_tax/static/src/helpers/*.js",
        ],
    },
}
