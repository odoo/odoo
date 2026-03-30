{
    "name": "Kodoo Studio",
    "version": "19.0.1.0.0",
    "category": "Kodoo/Core",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["kodoo_forge", "web"],
    "assets": {
        "web.assets_backend": [
            "kodoo_studio/static/lib/xterm/xterm.css",
            "kodoo_studio/static/lib/xterm/xterm.js",
            "kodoo_studio/static/lib/xterm/addon-fit.js",
            "kodoo_studio/static/src/studio.css",
            "kodoo_studio/static/src/services/forge_api.js",
            "kodoo_studio/static/src/components/AppManager.js",
            "kodoo_studio/static/src/components/ModuleForm.js",
            "kodoo_studio/static/src/components/PipelinePanel.js",
            "kodoo_studio/static/src/components/StudioTerminal.js",
            "kodoo_studio/static/src/components/KodooStudio.js",
            "kodoo_studio/static/src/studio.xml",
        ],
    },
    "data": [
        "views/studio_action.xml",
        "views/studio_menu.xml",
    ],
    "installable": True,
    "application": False,
}
