{
    "name": "Base Import Auto Map",
    "version": "18.0.1.0.0",
    "summary": "Auto-asigna campos en importación y oculta selección manual",
    "depends": ["base_import"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "base_import_auto_map/static/src/js/import_auto_map_patch.js",
            "base_import_auto_map/static/src/xml/import_auto_map_templates.xml",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
