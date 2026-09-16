{
    "name": "Quiz on Live Event Tracks",
    "version": "1.0",
    "category": "Marketing/Events",
    "summary": "Bridge module to support quiz features during \"live\" tracks.",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/events",
    "license": "LGPL-3",
    "depends": [
        "website_event_track_live",
        "website_event_track_quiz",
    ],
    "data": [
        "views/event_track_templates_page.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_event_track_live_quiz/static/src/interactions/**/*",
            "website_event_track_live_quiz/static/src/xml/**/*",
        ],
    },
    "auto_install": True,
}
