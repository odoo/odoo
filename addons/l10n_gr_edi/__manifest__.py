{
    "name": "Greece - myDATA",
    "version": "19.0.2.1.0",
    "category": "Accounting/Localizations",
    "summary": "Connect to myDATA API implementation for Greece",
    "description": """
        myDATA is a platform created by Greece's tax authority,
        The Independent Authority for Public Revenue (IAPR),
        to digitize business tax and accounting information declaration.
    """,
    "author": "Odoo",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "l10n_gr",
        "exchange",
    ],
    "countries": [
        "gr",
    ],
    "data": [
        "data/exchange_data.xml",
        "data/template.xml",
        "security/ir.model.access.csv",
        "views/account_fiscal_position_views.xml",
        "views/account_move_views.xml",
        "views/account_tax_views.xml",
        "views/product_template_views.xml",
        "views/report_invoice.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
    ],
    "auto_install": [
        "l10n_gr",
    ],
}
