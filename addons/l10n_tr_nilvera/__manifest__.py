{
    "name": "Türkiye - Nilvera",
    "version": "1.1",
    "category": "Accounting/Accounting",
    "description": """
Base module containing core functionalities required by other Nilvera modules.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "l10n_tr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "data/uom_data.xml",
    ],
    "post_init_hook": "_l10n_tr_nilvera_post_init",
    "uninstall_hook": "uninstall_hook",
}
