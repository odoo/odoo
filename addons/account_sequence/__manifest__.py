# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Account Sequence",
    'description': """
        This module allows to bind sequence_id to journals so that account_move names will be computed 
        from legacy ir.sequence and not from current sequence.mixin.
        This can be useful in some corner cases where current mixin can cause concurrency issues.
        The field sequence_id (and possibly refund_sequence_id) must be set manually on concerned journals.
        Standard implementation of sequences solves concurrency issues but can create gaps !
    """,
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['base', 'account'],
    'license': 'LGPL-3',
}
