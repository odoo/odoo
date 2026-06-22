{
    "name": "Saudi Core",
    "summary": "Core Saudi features: Hijri calendar, partner extensions, localization setup",
    "author": "Your Company",
    "version": "1.0",
    "category": "Localization",
    "depends": ["base", "web"],
    "data": [
        "security/saudi_core_security.xml",
        "security/ir.model.access.csv",
        "data/partner_categories.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
        "views/saudi_core_menus.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "custom_addons/saudi_core/static/src/js/hijri_datepicker.js",
            "custom_addons/saudi_core/static/src/scss/main.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
