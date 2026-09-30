# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'IBAN Bank Accounts',
    'category': 'Accounting/Accounting',
    'description': """
This module installs the base for IBAN (International Bank Account Number) bank accounts and checks for it's validity.
======================================================================================================================

The ability to extract the correctly represented local accounts from IBAN accounts
with a single statement.
    """,
    'depends': ['account', 'web'],
    'data': [
        'views/partner_view.xml',
        'views/setup_wizards_view.xml'
    ],
    'demo': ['data/res_partner_bank_demo.xml'],
    'assets': {
        'web.assets_backend': [
            'base_iban/static/src/components/**/*',
        ],
        'web.assets_unit_tests': [
            'base_iban/static/src/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
