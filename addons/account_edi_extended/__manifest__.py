# -*- coding: utf-8 -*-
{
    'name' : 'Additionnal features for account_edi',
    'description':"""
        This module add features to account_edi to support new Edi formats.
    """,
    'version' : '1.0',
    'category': 'Accounting/Accounting',
    'depends' : ['account_edi'],
    'data': [
        'views/account_edi_document_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'account_edi_block_level',
}
