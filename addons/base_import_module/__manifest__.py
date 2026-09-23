{
    "name": "Base import module",
    "category": "Hidden/Tools",
    "description": """
Import a custom data module
===========================

This module allows authorized users to import a custom data module (.xml files and static assests)
for customization purpose.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.access.csv",
        "views/base_import_module_view.xml",
        "views/ir_module_views.xml",
        "views/base_import_module_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "base_import_module/static/src/**/*",
        ],
    },
    "auto_install": True,
}
