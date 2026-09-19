{
    "name": "Indian - Accounting",
    "version": "2.1",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
Indian Accounting: Chart of Account.
====================================

Indian accounting chart and localization.

Odoo allows to manage Indian Accounting by providing Two Formats Of Chart of Accounts i.e Indian Chart Of Accounts - Standard and Indian Chart Of Accounts - Schedule VI.

Note: The Schedule VI has been revised by MCA and is applicable for all Balance Sheet made after
31st March, 2011. The Format has done away with earlier two options of format of Balance
Sheet, now only Vertical format has been permitted Which is Supported By Odoo.
  """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/india.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account_tax_python",
        "account_vat",
        "account_debit_note",
        "account",
        "iap",
    ],
    "external_dependencies": {
        "python": [
            "python-stdnum",
        ],
        "apt": {
            "python-stdnum": "python3-stdnum",
        },
    },
    "countries": [
        "in",
    ],
    "data": [
        "security/l10n_in_security.xml",
        "security/ir.model.access.csv",
        "data/iap_service_data.xml",
        "data/account.account.tag.csv",
        "data/l10n_in_chart_data.xml",
        "data/l10n_in.port.code.csv",
        "data/res_country_state_data.xml",
        "data/res_country_group.xml",
        "data/uom_data.xml",
        "data/res_partner_industry.xml",
        "data/account_cash_rounding.xml",
        "data/account_tax_report_tcs_data.xml",
        "data/account_tax_report_tds_data.xml",
        "data/l10n_in.section.alert.csv",
        "wizards/l10n_in_withhold_wizard.xml",
        "views/l10n_in_pan_entity_views.xml",
        "views/l10n_in_section_alert_views.xml",
        "views/account_account_views.xml",
        "views/account_invoice_views.xml",
        "views/account_move_line_views.xml",
        "views/account_payment_views.xml",
        "views/account_journal_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_view.xml",
        "views/port_code_views.xml",
        "views/res_company_views.xml",
        "views/report_invoice.xml",
        "views/res_country_state_view.xml",
        "views/res_partner_views.xml",
        "views/account_tax_views.xml",
        "views/uom_uom_views.xml",
        "views/l10n_in_menus.xml",
    ],
    "demo": [
        "demo/product_demo.xml",
        "demo/demo_company.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_in/static/src/components/**/*",
            "l10n_in/static/src/helpers/*.js",
        ],
        "web.assets_frontend": [
            "l10n_in/static/src/components/tests_shared_js_python/*",
            "l10n_in/static/src/helpers/*.js",
        ],
    },
    "auto_install": [
        "account",
    ],
    "post_init_hook": "post_init",
}
