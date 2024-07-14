# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Ireland - Accounting Reports",
    "category": "Accounting/Localizations/Reporting",
    "author": "Odoo SA",
    "version": "1.0",
    "license": "OEEL-1",
    "depends": [
        "l10n_ie",
        "account_reports",
    ],
    "data": [
        "data/profit_and_loss-ie.xml",
        "data/balance_sheet-ie.xml",
        "data/ec_sales_list_report-ie.xml",
        "data/tax_report-ie.xml",
        "data/vat3_template.xml",
    ],
    "installable": True,
    "post_init_hook": "_l10n_ie_reports_post_init",
    "auto_install": ["l10n_ie", "account_reports"],
}
