{
    "name": "Saudi Arabia - E-invoicing",
    "version": "0.4",
    "category": "Accounting/Localizations/EDI",
    "summary": "E-Invoicing, Universal Business Language",
    "description": """
E-invoice implementation for Saudi Arabia; Integration with ZATCA
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account_edi",
        "account_edi_ubl_cii",
        "l10n_sa",
        "account_vat",
        "certificate",
    ],
    "countries": [
        "sa",
    ],
    "data": [
        "security/ir.access.csv",
        "data/account_edi_format.xml",
        "data/ubl_21_zatca.xml",
        "data/res_country_data.xml",
        "wizards/l10n_sa_edi_otp_wizard.xml",
        "views/account_tax_views.xml",
        "views/account_journal_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_view.xml",
        "views/report_invoice.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_sa_edi/static/src/scss/form_view.scss",
        ],
    },
    "post_init_hook": "_l10n_sa_edi_post_init",
}
