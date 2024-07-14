# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet Accounting Templates",
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Spreadsheet Accounting templates',
    'description': 'Spreadsheet Accounting templates',
    'depends': ['documents_spreadsheet', 'account'],
    'data': [
        'data/spreadsheet_template_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_tests': [
            'documents_spreadsheet_account/static/**/*',
        ],
    }
}
