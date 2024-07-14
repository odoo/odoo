# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard edition",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet Dashboard edition',
    'description': 'Spreadsheet Dashboard edition',
    'depends': ['spreadsheet_dashboard', 'spreadsheet_edition'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'data': [
        "views/spreadsheet_dashboard_views.xml",
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'spreadsheet_dashboard_edition/static/src/bundle/**/*.js',
        ],
        'web.assets_backend': [
            'spreadsheet_dashboard_edition/static/src/assets/**/*.js',
            'spreadsheet_dashboard_edition/static/src/**/*.scss',
            'spreadsheet_dashboard_edition/static/src/**/*.xml',
        ],
        'spreadsheet.assets_print': [
            'spreadsheet_dashboard_edition/static/src/print_assets/**/*',
        ],
        'web.qunit_suite_tests': [
            'spreadsheet_dashboard_edition/static/tests/**/*',
        ],
        'web.qunit_mobile_suite_tests': [
            'spreadsheet_dashboard_edition/static/tests/mock_server.js',
        ],
    }
}
