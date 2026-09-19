{
    "name": "Privacy",
    "version": "1.1",
    "category": "Hidden",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "wizards/privacy_lookup_wizard_views.xml",
        "views/privacy_log_views.xml",
        "security/ir.model.access.csv",
        "data/ir_actions_server_data.xml",
        "views/privacy_lookup_menus.xml",
    ],
    "auto_install": True,
}
