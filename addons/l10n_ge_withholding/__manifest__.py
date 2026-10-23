{
    "name": "Georgia - Withholding Tax",
    "category": "Accounting/Localizations",
    "summary": "Georgian withholding tax on payments",
    "countries": ["GE"],
    "description": """
This module adds support for Georgian withholding tax, including:
=================================================================
* Withholding taxes
* Withholding tax categories
* Withholding tax return form
    """,
    "author": "Odoo S.A.",
    "depends": [
        "l10n_ge",
        "l10n_account_withholding_tax",
    ],
    "auto_install": ["l10n_ge"],
    "data": [
        "data/l10n_ge.wht.category.csv",
        "data/account_tax_report_withholding_data.xml",
        "security/ir.access.csv",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "views/account_tax_views.xml",
        "views/l10n_ge_wht_category_views.xml",
        "views/res_partner_views.xml",
        "wizards/account_payment_register_views.xml",
    ],
    "license": "LGPL-3",
}
