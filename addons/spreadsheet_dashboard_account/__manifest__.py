# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for accounting",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'spreadsheet_account'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['spreadsheet_account'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    "assets": {
        "spreadsheet.o_spreadsheet": [
            "spreadsheet_dashboard_account/static/src/bundle/**/*.js",
        ],
        'web.assets_unit_tests': [
            "spreadsheet_dashboard_account/static/tests/**/*",
        ],
    },
}
