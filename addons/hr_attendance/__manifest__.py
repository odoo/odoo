{
    "name": "Attendances",
    "version": "2.5",
    "category": "Human Resources/Attendances",
    "sequence": 240,
    "summary": "Track employee attendance",
    "description": """
This module aims to manage employee's attendances.
==================================================

Keeps account of the attendances of the employees on the basis of the
actions(Check in/Check out) performed by them.
       """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/employees",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "barcodes",
        "geocoding",
    ],
    "data": [
        "data/hr_attendance_overtime_ruleset_data.xml",
        "data/hr_attendance_overtime_rule_data.xml",
        "data/hr_attendance_data.xml",
        "security/hr_attendance_security.xml",
        "security/hr_attendance_overtime_ruleset_security.xml",
        "security/ir.model.access.csv",
        "views/hr_attendance_view.xml",
        "views/hr_department_view.xml",
        "views/hr_employee_view.xml",
        "views/res_config_settings_views.xml",
        "views/hr_attendance_kiosk_templates.xml",
        "views/hr_attendance_overtime_rule_views.xml",
        "views/hr_attendance_overtime_views.xml",
        "views/hr_attendance_menus.xml",
    ],
    "demo": [
        "demo/hr_attendance_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_attendance/static/src/**/*.js",
            "hr_attendance/static/src/**/*.xml",
            "hr_attendance/static/src/scss/views/*.scss",
            "hr_attendance/static/src/components/**/*.scss",
        ],
        "web.assets_unit_tests": [
            "hr_attendance/static/tests/*.test.js",
        ],
        "hr_attendance.assets_public_attendance": [
            "hr_attendance/static/src/scss/kiosk/primary_variables.scss",
            (
                "include",
                "web._assets_helpers",
            ),
            (
                "include",
                "web._assets_primary_variables",
            ),
            "hr_attendance/static/src/scss/kiosk/bootstrap_overridden.scss",
            (
                "include",
                "web._assets_frontend_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            (
                "include",
                "web._assets_bootstrap_frontend",
            ),
            (
                "include",
                "web._assets_bootstrap_backend",
            ),
            "/web/static/lib/odoo_ui_icons/*",
            "/web/static/lib/bootstrap/scss/_functions.scss",
            "/web/static/lib/bootstrap/scss/_mixins.scss",
            "/web/static/lib/bootstrap/scss/utilities/_api.scss",
            "web/static/src/libs/fontawesome7/css/fontawesome.css",
            "web/static/src/libs/fontawesome7/css/solid.css",
            "web/static/src/libs/fontawesome7/css/regular.css",
            "web/static/src/libs/fontawesome7/css/brands.css",
            "web/static/src/scss/tokens.scss",
            (
                "include",
                "web._assets_core",
            ),
            "hr_attendance/static/src/public_kiosk/**/*",
            "hr_attendance/static/src/components/**/*",
            (
                "remove",
                "hr_attendance/static/src/components/attendance_menu/**/*",
            ),
            "hr_attendance/static/src/scss/kiosk/hr_attendance.scss",
            "web/static/src/core/formatters.js",
            "web/static/src/session.js",
            "web/static/src/views/widgets/standard_widget_props.js",
            "web/static/src/views/widgets/documentation_link/*",
            "barcodes/static/src/components/barcode_scanner.js",
            "barcodes/static/src/components/barcode_scanner.xml",
            "barcodes/static/src/components/barcode_scanner.scss",
            "barcodes/static/src/barcode_service.js",
        ],
    },
    "esm": {
        "bundles": [
            "hr_attendance.assets_public_attendance",
        ],
        "secondary_import_map_includes": {
            "hr_attendance.assets_public_attendance": [
                "web.assets_tests",
            ],
        },
    },
    "application": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
