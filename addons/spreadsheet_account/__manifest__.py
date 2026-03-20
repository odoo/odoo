# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet Accounting Formulas",
    'category': 'Accounting',
    'summary': 'Spreadsheet Accounting formulas',
    'description': 'Spreadsheet Accounting formulas',
    'depends': ['spreadsheet', 'account'],
    'auto_install': ['account'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            (
                'after',
                'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
                'spreadsheet_account/static/src/**/*.js'
            ),
        ],
        'web.assets_unit_tests': [
            'spreadsheet_account/static/tests/**/*',
        ],
    }
}
