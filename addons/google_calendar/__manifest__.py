{
    "name": "Google Calendar",
    "version": "19.0.2.1.0",
    "category": "Productivity",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "google_account",
        "calendar",
        "credential",
    ],
    "data": [
        "data/google_calendar_data.xml",
        "security/ir.access.csv",
        "wizards/reset_account_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
        "views/google_calendar_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "google_calendar/static/src/scss/google_calendar.scss",
            "google_calendar/static/src/views/**/*",
        ],
        "web.assets_unit_tests": [
            "google_calendar/static/tests/**/*",
        ],
    },
}
