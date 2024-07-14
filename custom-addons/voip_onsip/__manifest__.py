# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "VoIP OnSIP",
    "description": """Enables VoIP compatibility with OnSIP.""",
    "category": "Hidden",
    "version": "1.0",
    "depends": ["voip"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
    ],
    "license": "OEEL-1",
    "assets": {
        "web.assets_backend": [
            "voip_onsip/static/src/**/*",
        ],
    },
}
