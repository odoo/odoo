{
    "name": "BR Base",
    "version": "19.0.1.0.0",
    "summary": "Base cadastral e utilitarios brasileiros",
    "category": "Localization/Brazil",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["base", "mail", "l10n_br"],
    "data": [
        "security/br_base_security.xml",
        "security/ir.model.access.csv",
        "data/br_estados.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/br_municipio_views.xml",
    ],
    "installable": True,
    "application": False,
}

