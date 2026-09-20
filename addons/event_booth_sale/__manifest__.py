{
    "name": "Events Booths Sales",
    "version": "1.4",
    "category": "Marketing/Events",
    "summary": "Manage event booths sale",
    "description": """
Sell your event booths and track payments on sale orders.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "event_booth",
        "event_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/product_data.xml",
        "data/event_booth_category_data.xml",
        "views/sale_order_views.xml",
        "views/event_type_booth_views.xml",
        "views/event_booth_category_views.xml",
        "views/event_booth_registration_views.xml",
        "views/event_booth_views.xml",
        "wizards/event_booth_configurator_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "event_booth_sale/static/src/**/*",
        ],
    },
    "auto_install": True,
}
