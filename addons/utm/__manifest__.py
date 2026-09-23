{
    "name": "UTM Trackers",
    "version": "1.1",
    "category": "Marketing",
    "description": """
Enable management of UTM trackers: campaign, medium, source.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "data/utm_medium_data.xml",
        "data/utm_source_data.xml",
        "data/utm_stage_data.xml",
        "data/utm_tag_data.xml",
        "views/utm_campaign_views.xml",
        "views/utm_medium_views.xml",
        "views/utm_source_views.xml",
        "views/utm_stage_views.xml",
        "views/utm_tag_views.xml",
        "views/utm_menus.xml",
        "security/ir.access.csv",
    ],
    "demo": [
        "demo/utm_campaign_demo.xml",
        "demo/utm_stage_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "utm/static/src/**/*",
        ],
    },
}
