# -*- coding: utf-8 -*-
from odoo import models

class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    def _str_query_for_mv_line(self, from_clause, where_clause, where_clause_params, search_str):
        from_clause, where_clause, where_clause_params = super(AccountReconciliation, self)._str_query_for_mv_line(from_clause, where_clause, where_clause_params, search_str)
        from_clause += """
            LEFT JOIN account_payment payment ON line.payment_id = payment.id"""
        where_clause += """
                OR payment.check_number = %(search_str)s"""
        return from_clause, where_clause, where_clause_params
