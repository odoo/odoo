{
    "name": "Website Configurator Action Fix",
    "summary": "Ensures the website configurator client action is registered in the backend",
    "version": "19.0.1.0.0",
    "category": "Website/Website",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "views/website_configurator_action_fix.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "website_configurator_action_fix/static/src/js/website_configurator_action_fix.js",
        ],
    },
    "installable": True,
    "auto_install": True,
    "application": False,
}
