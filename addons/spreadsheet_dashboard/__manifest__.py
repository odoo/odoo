{
    "name": "Spreadsheet dashboard",
    "version": "1.1",
    "category": "Productivity/Dashboard",
    "summary": "Spreadsheet",
    "description": "Spreadsheet",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "spreadsheet",
    ],
    "data": [
        "security/security.xml",
        "security/ir.access.csv",
        "views/spreadsheet_dashboard_views.xml",
        "views/menu_views.xml",
        "data/dashboard.xml",
    ],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            "spreadsheet_dashboard/static/src/bundle/**/*.js",
            "spreadsheet_dashboard/static/src/bundle/**/*.xml",
        ],
        "spreadsheet.assets_print": [
            "spreadsheet_dashboard/static/src/print_assets/**/*",
        ],
        "web.assets_backend": [
            "spreadsheet_dashboard/static/src/assets/**/*.js",
            "spreadsheet_dashboard/static/src/**/*.scss",
        ],
        "web.assets_unit_tests": [
            "spreadsheet_dashboard/static/tests/**/*",
        ],
    },
}
