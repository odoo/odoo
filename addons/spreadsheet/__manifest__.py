# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['bus', 'web'],
    'data': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
            'spreadsheet/static/src/**/*.js',
            # Load all o_spreadsheet templates first to allow to inherit them
            'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.xml',
            'spreadsheet/static/src/**/*.xml',
            ('remove', 'spreadsheet/static/src/assets_backend/**/*')
        ],
        'web.assets_backend': [
            'spreadsheet/static/src/**/*.scss',
            'spreadsheet/static/src/assets_backend/**/*',
        ],
        'web.qunit_suite_tests': [
            'spreadsheet/static/tests/**/*',
            ('include', 'spreadsheet.o_spreadsheet')
        ]
    }
}
