# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Import CSV Bank Statement',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'description': r'''
Module to import CSV bank statements.
======================================

This module allows you to import CSV Files in Odoo: they are parsed and stored in human readable format in
Accounting \ Bank and Cash \ Bank Statements.

Important Note
---------------------------------------------
Because of the CSV format limitation, we cannot ensure the same transactions aren't imported several times or handle multicurrency.
Whenever possible, you should use a more appropriate file format like OFX.
''',
    'depends': ['account_bank_statement_import', 'base_import'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_bank_statement_import_csv/static/src/**/*',
        ],
    }
}
