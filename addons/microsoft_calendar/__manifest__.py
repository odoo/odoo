{
    "name": "Outlook Calendar",
    "version": "1.1",
    "category": "Productivity",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "microsoft_account",
        "calendar",
    ],
    "data": [
        "data/microsoft_calendar_data.xml",
        "security/ir.access.csv",
        "wizards/reset_account_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
        "views/microsoft_calendar_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "microsoft_calendar/static/src/scss/microsoft_calendar.scss",
            "microsoft_calendar/static/src/views/**/*",
        ],
        "web.assets_unit_tests": [
            "microsoft_calendar/static/tests/**/*",
        ],
    },
    "post_init_hook": "init_initiating_microsoft_uuid",
}
