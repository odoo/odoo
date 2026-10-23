# © 2022 Florian Kantelberg - initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Dark Mode",
    "summary": "Enabled Dark Mode for the Odoo Backend",
    "license": "AGPL-3",
    "version": "16.0.1.0.2",
    "website": "https://github.com/OCA/web",
    "author": "initOS GmbH, Odoo Community Association (OCA)",
    "depends": ["web"],
    "excludes": ["web_enterprise"],
    "installable": True,
    "assets": {
        "web.dark_mode_assets_common": [
            ("prepend", "web_dark_mode/static/src/scss/variables.scss"),
        ],
        "web.dark_mode_assets_backend": [
            ("prepend", "web_dark_mode/static/src/scss/variables.scss"),
        ],
        "web.assets_backend": [
            "web_dark_mode/static/src/js/switch_item.esm.js",
        ],
    },
    "data": [
        "views/res_users_views.xml",
    ],
}
