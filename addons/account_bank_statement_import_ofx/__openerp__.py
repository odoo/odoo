# -*- encoding: utf-8 -*-
{
    'name': 'Import OFX Bank Statement',
    'category': 'Accounting & Finance',
    'version': '1.0',
    'author': 'Odoo SA',
    'depends': ['account_bank_statement_import'],
    'description': """
Module to import OFX bank statements.
======================================

This module allows you to import the machine readable OFX Files in Odoo: they are parsed and stored in human readable format in
Accounting \ Bank and Cash \ Bank Statements.

Bank Statements may be generated containing a subset of the OFX information (only those transaction lines that are required for the
creation of the Financial Accounting records).
    """,
    'installable': True,
    'auto_install': True,
}
