# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'IBAN Bank Accounts',
    'category': 'Tools',
    'description': """
This module installs the base for IBAN (International Bank Account Number) bank accounts and checks for it's validity.
======================================================================================================================

The ability to extract the correctly represented local accounts from IBAN accounts
with a single statement.
    """,
    'depends': ['account', 'web'],
    'data': [
        'views/templates.xml',
        'views/partner_view.xml'
    ],
    'demo': ['data/res_partner_bank_demo.xml'],
}
