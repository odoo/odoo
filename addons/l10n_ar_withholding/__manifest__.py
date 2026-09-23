{
    "name": "Argentina - Payment Withholdings",
    "version": "1.1",
    "category": "Accounting/Localizations",
    "description": "Allows to register withholdings during the payment of an invoice.",
    "author": "ADHOC SA",
    "license": "LGPL-3",
    "depends": [
        "l10n_ar",
        "l10n_latam_check",
    ],
    "countries": [
        "ar",
    ],
    "data": [
        "views/account_tax_views.xml",
        "views/account_payment_view.xml",
        "views/report_payment_receipt_templates.xml",
        "views/res_config_settings.xml",
        "views/res_partner_view.xml",
        "views/l10n_ar_earnings_scale_view.xml",
        "wizards/account_payment_register_views.xml",
        "security/ir.access.csv",
        "data/earnings_table_data.xml",
        "views/l10n_ar_withholding_menus.xml",
    ],
    "post_init_hook": "_l10n_ar_wth_post_init",
}
