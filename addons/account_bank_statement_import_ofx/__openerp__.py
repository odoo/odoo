# -*- encoding: utf-8 -*-
{
    'name': 'Import OFX Bank Statement',
    'version': '1.0',
    'author': 'OpenERP SA',
    'depends': ['account_bank_statement_import'],
    'demo': [],
    'description' : """
Module to import OFX bank statements.
======================================

This module allows you to import the machine readable OFX Files in Odoo: they are parsed and stored in human readable format in 
Accounting \ Bank and Cash \ Bank Statements.

Bank Statements may be generated containing a subset of the OFX information (only those transaction lines that are required for the 
creation of the Financial Accounting records). 
    
    """,
    'data' : [],
    'demo': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
