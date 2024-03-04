{
    "name": "Translations",
    "version": "1.0",
    "category": "TODO: find the appropriate category",
    "description": "TODO: write a description of the module",
    "depends": ["base", "web"],
    "data": [
        "views/t9n_templates.xml"
    ],
    "application": True,
    "assets": {
        "web.assets_backend": [
            "t9n/static/src/**/*",
        ],
    },
    "license": "LGPL-3",
}
