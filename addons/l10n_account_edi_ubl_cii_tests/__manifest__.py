# -*- coding: utf-8 -*-
{
    'name': "Testing the Import/Export invoices with UBL/CII",
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """
    This module tests the module 'account_edi_ubl_cii', it is separated since dependencies to some 
    localizations were required. Its name begins with 'l10n' to not overload runbot.
    
    The test files are separated by sources, they were taken from:
    
    * the factur-x doc (form the FNFE)
    * the peppol-bis-invoice-3 doc (the github repository: https://github.com/OpenPEPPOL/peppol-bis-invoice-3/tree/master/rules/examples contains examples)
    * odoo, these files pass all validation tests (using ecosio or the FNFE validator)
    
    We test that the external examples are correctly imported (currency, total amount and total tax match).
    We also test that generating xml from odoo with given parameters gives exactly the same xml as the expected, 
    valid ones.
    """,
    'depends': [
        'l10n_generic_coa',
        'account_edi_ubl_cii',
        'l10n_fr',
        'l10n_be',
        'l10n_de',
        'l10n_nl',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
