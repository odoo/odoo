# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet Accounting Formulas",
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Spreadsheet Accounting formulas',
    'description': 'Spreadsheet Accounting formulas',
    'depends': ['spreadsheet', 'account'],
    'data': [],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            (
                'after',
                'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
                'spreadsheet_account/static/src/**/*.js'
            ),
        ],
        'web.qunit_suite_tests': [
            'spreadsheet_account/static/tests/**/*.js',
        ],
    }
}
