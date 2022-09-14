# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for sales",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'demo': [],
    'installable': True,
    'auto_install': ['sale'],
    'license': 'LGPL-3',
    'assets': {
        'spreadsheet_dashboard.o_spreadsheet': [],
        'web.assets_backend': [],
        'web.qunit_suite_tests': [],
        'web.assets_tests': [
            'spreadsheet_dashboard_sale/static/tests/**/*',
        ],
    }
}
