# -*- coding: utf-8 -*-

{
    'name': 'Import QIF Bank Statement',
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

As the editor states it : "QIF technology is over 10 years old and was designed for technical support purposes, it was not for transaction 
download. QIF Data Import requires many steps to download, is a poor customer experience and can lead to duplicate transactions and errors."
''',
    'images' : [],
    'depends': ['account_bank_statement_import'],
    'demo': [],
    'data': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
