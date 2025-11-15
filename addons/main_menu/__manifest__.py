{
    "name": "Main Menu",
    "version": "19.0.1.2.0",
    "summary": "Enhanced navigation module for Odoo Community Edition.",
    "description": """
        This module provides a centralized main menu for Odoo Community Edition, allowing users to quickly access core modules and enhance their workflow.
        It features widget functionality for displaying the current date and posting announcements, which can be managed by administrators.
        Users can create bookmarks for quick access to essential menus, as well as external links, improving overall navigation efficiency.
    """,
    "author": "Axel Manzanilla",
    "maintainer": "Axel Manzanilla",
    "website": "https://axelmanzanilla.com",
    "license": "LGPL-3",
    "category": "Technical/Technical",
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/main_menu_views.xml",
        "views/menu_bookmark_views.xml",
        "views/res_config_setting_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "main_menu/static/src/components/**/*",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "auto_install": True,
}
