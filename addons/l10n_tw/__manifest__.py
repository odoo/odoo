{
    "name": "Taiwan - Accounting",
    "author": "Odoo PS",
    "version": "1.0",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
This is the base module to manage the accounting chart for Taiwan in Odoo.
==============================================================================
    """,
    "depends": [
        "account",
        "base_address_extended",
        "l10n_multilang",
    ],
    "data": [
        "data/l10n_tw_chart_data.xml",
        "data/account.account.template.csv",
        "data/res.country.state.csv",
        "data/account_chart_template_data.xml",
        "data/account.tax.group.csv",
        "data/account_tax_template_data.xml",
        "data/account_chart_template_configure_data.xml",
        "data/res_currency_data.xml",
        "data/res_country_data.xml",
        "data/res.city.csv",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    "icon": "/base/static/img/country_flags/tw.png",
    "post_init_hook": "load_translations",
    "license": "LGPL-3",
}
