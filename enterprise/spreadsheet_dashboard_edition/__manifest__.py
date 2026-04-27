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
        "security/security.xml",
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
        'web.assets_unit_tests': [
            'spreadsheet_dashboard_edition/static/tests/**/*',
        ],
    }
}
