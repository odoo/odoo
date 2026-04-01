{
    "name": "Kodoo Studio Integration",
    "version": "19.0.1.0.0",
    "category": "Kodoo/Core",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["kodoo_studio", "web"],
    "data": [
        "data/studio_app_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kodoo_studio_integration/static/src/systray/StudioSystray.xml",
            "kodoo_studio_integration/static/src/systray/studio_systray.css",
            "kodoo_studio_integration/static/src/systray/StudioSystray.js",
            "kodoo_studio_integration/static/src/hide_web_studio/hide_web_studio.js",
        ],
    },
    "installable": True,
    "application": True,
    "sequence": 5,
}
