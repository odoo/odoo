{
    "name": "Remote Work with calendar",
    "version": "1.0",
    "category": "Human Resources/Remote Work",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr_homeworking",
        "calendar",
    ],
    "data": [
        "security/ir.access.csv",
        "wizards/homework_location_wizard.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_homeworking_calendar/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "hr_homeworking_calendar/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
