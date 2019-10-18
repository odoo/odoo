# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def _domain_move_lines_for_reconciliation(self, st_line, aml_accounts, partner_id, excluded_ids=None, search_str=False, mode='rp'):
        def to_int(val):
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        domain = super()._domain_move_lines_for_reconciliation(
            st_line, aml_accounts, partner_id, excluded_ids=excluded_ids, search_str=search_str, mode=mode
        )
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
        if acc_ids:
            domain = expression.AND([domain, [("account_id.id", "not in", acc_ids)]])
        return domain
