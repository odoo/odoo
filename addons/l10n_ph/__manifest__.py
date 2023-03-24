# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Philippines - Accounting",
    "summary": """
        This is the module to manage the accounting chart for The Philippines.
    """,
    "category": "Accounting/Localizations/Account Charts",
    "version": "1.0",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "depends": [
        "account",
        "base_vat",
        "l10n_multilang",
    ],
    "data": [
        "data/account_chart_template_data.xml",
        "data/account.account.template.csv",
        "data/account_chart_template_post_data.xml",
        "data/account_tax_group.xml",
        "data/account_tax_template.xml",
        "data/account_fiscal_position_template.xml",
        "data/account_fiscal_position_tax_template.xml",
        "data/account_chart_template_configure_data.xml",
        "wizard/generate_2307_wizard_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "views/account_tax_views.xml",
        "views/res_partner_views.xml",
        "security/ir.model.access.csv",
    ],
    "license": "LGPL-3",
    "icon": "/base/static/img/country_flags/ph.png",
}
