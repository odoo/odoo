{
    "name": "Philippines - Accounting",
    "version": "1.1",
    "category": "Accounting/Localizations/Account Charts",
    "summary": "This is the module to manage the accounting chart for The Philippines.",
    "author": "Odoo PS",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/philippines.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_vat",
        "l10n_account_withholding_tax",
    ],
    "countries": [
        "ph",
    ],
    "data": [
        "data/account_tax_report_data.xml",
        "wizards/generate_2307_wizard_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "views/account_tax_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/report_disbursement_voucher_template.xml",
        "views/account_report.xml",
        "views/report_templates.xml",
        "security/ir.access.csv",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": [
        "account",
    ],
}
