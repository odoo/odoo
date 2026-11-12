# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 UI Defaults",
    "version": "19.0.1.2.0",
    "summary": (
        "Project-wide UI defaults: Configuration menu is always the last menu of "
        "its app, related NavBar sections are grouped, moved or renamed together, "
        "form fields are more readable, and the standard Sales 'Discounts' "
        "setting is enabled"
    ),
    "author": "OD19",
    "category": "Tools",
    "depends": ["base", "sale"],
    "data": [
        "data/ui_defaults.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_ui_defaults/static/src/css/form_readability.css",
            "od19_ui_defaults/static/src/js/field_empty_marker.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_ui_defaults/static/description/icon.svg",
}
