# -*- coding: utf-8 -*-
{
    'name': "account_qr_code_sepa",

    'description': """
        This module adds support for SEPA Credit Transfer QR-code generation.
    """,

    'category': 'Accounting/Payment',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'base_iban'],

    'data': [
    ],

    'auto_install': True,
    'license': 'LGPL-3',
}