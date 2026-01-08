# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Spreadsheet dashboard",
    "version": "1.0",
    "category": "Hidden",
    "summary": "Spreadsheet",
    "description": "Spreadsheet",
    "depends": ["spreadsheet"],
    "installable": True,
    "license": "LGPL-3",
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/spreadsheet_dashboard_views.xml",
        "views/menu_views.xml",
        "data/dashboard.xml",
    ],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            "spreadsheet_dashboard/static/src/bundle/**/*.js",
            "spreadsheet_dashboard/static/src/bundle/**/*.xml",
        ],
        'spreadsheet.assets_print': [
            'spreadsheet_dashboard/static/src/print_assets/**/*',
        ],
        "web.assets_backend": [
            "spreadsheet_dashboard/static/src/assets/**/*.js",
            "spreadsheet_dashboard/static/src/**/*.scss",
        ],
        "web.qunit_suite_tests": [
            "spreadsheet_dashboard/static/tests/**/*",
            ("remove", "spreadsheet_dashboard/static/tests/mobile/**/*.js"),
        ],
        "web.qunit_mobile_suite_tests": [
            "spreadsheet_dashboard/static/tests/mobile/**/*.js",
            "spreadsheet_dashboard/static/tests/utils/**/*.js",
            ("include", "spreadsheet.o_spreadsheet"),
        ],
    },
}
