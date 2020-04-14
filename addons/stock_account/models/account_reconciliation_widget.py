# -*- coding: utf-8 -*-

from odoo import api, models


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def _query_move_lines_for_reconciliation(self, st_line, aml_accounts, partner_id, excluded_ids=None, search_str=None, mode='rp'):
        def to_int(val):
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        acc_props = (
            "property_stock_account_input",
            "property_stock_account_output",
            "property_stock_account_input_categ_id",
            "property_stock_account_output_categ_id",
        )
        acc_ids = [
            (acc["value_reference"] or "").split(",")[-1]
            for acc in self.env["ir.property"]
            .sudo()
            .search([("name", "in", acc_props), ("value_reference", "!=", False)])
            .read(["value_reference"])
            if to_int((acc["value_reference"] or "").split(",")[-1])
        ]

        from_clause, where_clause, where_clause_params = super()._query_move_lines_for_reconciliation(st_line, aml_accounts, partner_id, excluded_ids, search_str, mode)
        where_clause += acc_ids and """
            AND account.id NOT IN %(stock_accounts)s""" or ""

        return from_clause, where_clause, {**where_clause_params, 'stock_accounts': tuple(acc_ids)}
