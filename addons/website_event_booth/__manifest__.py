{
    "name": "Online Event Booths",
    "version": "1.0",
    "category": "Marketing/Events",
    "summary": "Events, display your booths on your website",
    "description": """
Display your booths on your website for the users to register.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website_event",
        "event_booth",
    ],
    "data": [
        "security/ir.access.csv",
        "views/event_type_views.xml",
        "views/event_event_views.xml",
        "views/event_booth_registration_templates.xml",
        "views/event_booth_templates.xml",
    ],
    "demo": [
        "demo/event_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "/website_event_booth/static/src/interactions/*",
            "/website_event_booth/static/src/scss/website_event_booth.scss",
            "/website_event_booth/static/src/xml/event_booth_registration_templates.xml",
        ],
    },
    "auto_install": True,
}
