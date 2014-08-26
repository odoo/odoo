# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Belgium - Import Bank CODA Statements',
    'version': '2.1',
    'author': 'Noviat',
    'category': 'Accounting & Finance',
    'description': '''
Module to import CODA bank statements.
======================================

Supported are CODA flat files in V2 format from Belgian bank accounts.
----------------------------------------------------------------------
    * CODA v1 support.
    * CODA v2.2 support.
    * Foreign Currency support.
    * Support for all data record types (0, 1, 2, 3, 4, 8, 9).
    * Parsing & logging of all Transaction Codes and Structured Format
      Communications.
    * Automatic Financial Journal assignment via CODA configuration parameters.
    * Support for multiple Journals per Bank Account Number.
    * Support for multiple statements from different bank accounts in a single
      CODA file.
    * Support for 'parsing only' CODA Bank Accounts (defined as type='info' in
      the CODA Bank Account configuration records).
    * Multi-language CODA parsing, parsing configuration data provided for EN,
      NL, FR.

The machine readable CODA Files are parsed and stored in human readable format in
CODA Bank Statements. Also Bank Statements are generated containing a subset of
the CODA information (only those transaction lines that are required for the
creation of the Financial Accounting records). The CODA Bank Statement is a
'read-only' object, hence remaining a reliable representation of the original
CODA file whereas the Bank Statement will get modified as required by accounting
business processes.

CODA Bank Accounts configured as type 'Info' will only generate CODA Bank Statements.

A removal of one object in the CODA processing results in the removal of the
associated objects. The removal of a CODA File containing multiple Bank
Statements will also remove those associated statements.

Instead of a manual adjustment of the generated Bank Statements, you can also
re-import the CODA after updating the OpenERP database with the information that
was missing to allow automatic reconciliation.

Remark on CODA V1 support:
~~~~~~~~~~~~~~~~~~~~~~~~~~
In some cases a transaction code, transaction category or structured
communication code has been given a new or clearer description in CODA V2.The
description provided by the CODA configuration tables is based upon the CODA
V2.2 specifications.
If required, you can manually adjust the descriptions via the CODA configuration menu.
''',
    'images': ['images/coda_logs.jpeg', 'images/import_coda_logs.jpeg'],
    'depends': ['account_voucher', 'base_iban', 'l10n_be_invoice_bba'],
    'demo': ['l10n_be_coda_demo.xml'],
    'data': [
        'l10n_be_coda_wizard.xml',
        'l10n_be_coda_view.xml',
    ],
    'auto_install': False,
    'installable': True,
    'license': 'AGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
