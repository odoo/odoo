# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Russian Accounting",
    "version": "1.0.0",
    "category": "Accounting/Localizations/Account Charts",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        # Chart of Accounts
        "data/account_chart_template_data.xml",
        "data/account_account_template_data.xml",
        "data/account.group.template.csv",
        "data/l10n_ru_chart_post_data.xml",
        "data/account_chart_template_configure_data.xml",

        # # Taxes
        "data/account_tax_group_data.xml",
        #"data/account_tax_report_data.xml",
        "data/account_tax_template_data.xml",
        #"data/account_fiscal_position_template_data.xml",

        # Other
        "data/menuitem_data.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ]
}
