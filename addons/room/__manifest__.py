{
    "name": "Meeting Rooms",
    "version": "2.2",
    "category": "Productivity/Room",
    "summary": "Book meeting rooms from a tablet or the back-end",
    "description": "A meeting room is an asset booked through the calendar, with a real-time availability display for the tablet at its door.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "resource_asset_calendar",
    ],
    "data": [
        "security/room_security.xml",
        "security/ir.model.access.csv",
        "data/room_data.xml",
        "views/resource_asset_views.xml",
        "views/calendar_event_views.xml",
        "views/room_menus.xml",
        "views/room_booking_templates_frontend.xml",
    ],
    "demo": [
        "demo/room_demo.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "room/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "room/static/src/room_booking/**/*.js",
            "room/static/src/room_booking/**/*.xml",
            "room/static/tests/**/*",
            (
                "remove",
                "room/static/tests/tours/**/*",
            ),
        ],
        "room.assets_room_booking": [
            "room/static/src/room_booking/primary_variables.scss",
            "room/static/src/room_booking/bootstrap_overridden.scss",
            (
                "include",
                "web._assets_helpers",
            ),
            (
                "include",
                "web._assets_backend_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            (
                "include",
                "web._assets_bootstrap_backend",
            ),
            "web/static/src/libs/fontawesome7/css/fontawesome.css",
            "web/static/src/libs/fontawesome7/css/solid.css",
            "web/static/src/libs/fontawesome7/css/regular.css",
            "web/static/src/libs/fontawesome7/css/brands.css",
            "web/static/lib/odoo_ui_icons/*",
            "web/static/src/scss/base_frontend.scss",
            "web/static/src/ui/notification/notification.scss",
            "web/static/src/ui/block/block_ui.scss",
            "room/static/src/room_booking/**/*",
        ],
    },
    "esm": {
        "bundles": [
            "room.assets_room_booking",
        ],
        "secondary_import_map_includes": {
            "room.assets_room_booking": [
                "web.assets_tests",
            ],
        },
    },
    "application": True,
}
