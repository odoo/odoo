{
    "name": "Translations",
    "version": "1.0",
    "category": "TODO: find the appropriate category",
    "description": "TODO: write a description of the module",
    "depends": ["base", "web"],
    "application": True,
    "assets": {
        "web.assets_backend": [
            "t9n/static/src/**/*",
        ],
    },
    "data": [
        "data/t9n.language.csv",
        "security/ir.model.access.csv",
        "views/t9n_project_views.xml",
        "views/t9n_menu_views.xml",
        "views/t9n_language_views.xml",
        "views/t9n_resource_views.xml",
        "views/t9n_message_views.xml",
    ],
    "license": "LGPL-3",
}
