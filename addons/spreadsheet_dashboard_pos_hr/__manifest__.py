# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for point of sale",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'pos_hr'],
    'data': [
        "data/dashboards.xml",
    ],
    'demo': [],
    'installable': True,
    'auto_install': ['pos_hr'],
    'license': 'LGPL-3',
    'assets': {
        'spreadsheet_dashboard.o_spreadsheet': [],
        'web.assets_backend': [],
        'web.assets_qweb': [],
        'web.qunit_suite_tests': [],
        'web.assets_tests': [
            'spreadsheet_dashboard_pos_hr/static/tests/**/*',
        ],
    }
}
