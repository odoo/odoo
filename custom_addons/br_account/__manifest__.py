{
    "name": "BR Account",
    "version": "19.0.1.0.0",
    "summary": "Campos fiscais e controles contabeis brasileiros",
    "category": "Localization/Brazil",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["br_base", "account", "accountant", "l10n_br", "l10n_br_sales"],
    "data": [
        "security/ir.model.access.csv",
        "data/br_chart_of_accounts.xml",
        "data/br_tax_groups.xml",
        "views/account_move_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
}

