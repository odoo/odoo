{
    "name": "Events Booths",
    "version": "1.2",
    "category": "Marketing/Events",
    "summary": "Manage event booths",
    "description": """
Create booths for your favorite event.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "event",
    ],
    "data": [
        "security/ir.access.csv",
        "views/event_booth_category_views.xml",
        "views/event_type_booth_views.xml",
        "views/event_booth_views.xml",
        "views/event_type_views.xml",
        "views/event_event_views.xml",
        "views/event_menus.xml",
        "data/event_booth_category_data.xml",
        "data/mail_message_subtype_data.xml",
        "data/mail_templates.xml",
    ],
    "demo": [
        "demo/event_booth_demo.xml",
        "demo/event_type_demo.xml",
    ],
}
