# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'IBAN Bank Accounts',
    'version': '1.0',
    'category': 'Extra Tools',
    'description': """
This module installs the base for IBAN (International Bank Account Number) bank accounts and checks for it's validity.
======================================================================================================================

The ability to extract the correctly represented local accounts from IBAN accounts
with a single statement.
    """,
    'depends': ['account'],
    'demo': ['demo/iban_demo.xml'],
    'installable': True,
    'auto_install': False,
}
