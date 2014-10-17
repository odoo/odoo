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

Bank Statements may be generated containing a subset of the QIF information (only those transaction lines that are required for the 
creation of the Financial Accounting records). 
''',
    'images' : [],
    'depends': ['account_bank_statement_import'],
    'demo': [],
    'data': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
