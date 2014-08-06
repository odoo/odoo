# -*- coding: utf-8 -*-

{
    'name': 'Import QIF Bank Statement',
    # TODO : remove category Technical Settings once the kanban 'dashboard' view is merged
    # Without it, QIF import won't work (we need to specify the journal_id, which is done via context by the dashboard view)
    'category': 'Technical Settings',  # 'category' : 'Accounting & Finance',
    'version': '1.0',
    'author': 'OpenERP SA',
    'description': '''
Module to import QIF bank statements.
======================================

This module allows you to import the machine readable QIF Files in Odoo: they are parsed and stored in human readable format in
Accounting \ Bank and Cash \ Bank Statements.

Important Note
---------------------------------------------
Because of the QIF format limitation, we cannot ensure the same transactions aren't imported several times or handle multicurrency.
Whenever possible, you should use a more appropriate file format like OFX.
''',
    'images': [],
    'depends': ['account_bank_statement_import'],
    'demo': [],
    'data': ['account_bank_statement_import_qif_view.xml'],
    'auto_install': False,
    'installable': True,
}
