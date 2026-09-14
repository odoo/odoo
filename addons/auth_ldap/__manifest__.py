{
    "name": "Authentication via LDAP",
    "version": "1.1",
    "category": "Hidden/Tools",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "web",
    ],
    "external_dependencies": {
        "python": [
            "python-ldap",
        ],
        "apt": {
            "python-ldap": "python3-ldap",
        },
    },
    "data": [
        "views/ldap_installer_views.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
    ],
}
