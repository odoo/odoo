# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Spreadsheet Documents",
    "version": "1.0",
    "category": "Productivity/Documents",
    "summary": "Spreadsheet Documents",
    "description": "Spreadsheet Documents",
    "depends": ["spreadsheet_dashboard_edition", "documents_spreadsheet"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/documents_to_dashboard_views.xml",
        "views/spreadsheet_dashboard_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "OEEL-1",
    "assets": {
        "spreadsheet.o_spreadsheet": [
            (
                "after",
                "spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js",
                "spreadsheet_dashboard_documents/static/src/bundle/**/*.js",
            ),
        ],
        'web.assets_backend': [
            'spreadsheet_dashboard_documents/static/src/assets/**/*.js',
            'spreadsheet_dashboard_documents/static/src/**/*.xml',
        ],
        "web.qunit_suite_tests": [
            "spreadsheet_dashboard_documents/static/tests/**/*.js",
        ],
        'web.assets_tests': [
            'spreadsheet_dashboard_documents/static/tests/tours/*',
        ],

    },
}
