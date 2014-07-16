# -*- coding: utf-8 -*-

{
    'name': 'Import QIF Bank Statement',
    'version': '1.0',
    'description': '''
Module to import QIF bank statements.
======================================

The machine readable QIF Files are parsed and stored in human readable format in 
Bank Statements. Also Bank Statements are generated containing a subset of 
the QIF information (only those transaction lines that are required for the 
creation of the Financial Accounting records). The Bank Statement is a 
'read-only' object, hence remaining a reliable representation of the original
QIF file whereas the Bank Statement will get modified as required by accounting 
business processes.

QIF Bank Accounts configured as type 'QIF' will only generate QIF Bank Statements.
''',
    'images' : [],
    'depends': ['account_bank_statement_import'],
    'demo': [],
    'data': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
