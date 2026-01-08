from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _prepare_invoice_vals(self):
        move_vals = super()._prepare_invoice_vals()
        if "l10n_co_edi_description_code_credit" in self.env["account.move"] and move_vals.get("move_type") == "out_refund" and move_vals.get("reversed_entry_id"):
            move_vals["l10n_co_edi_description_code_credit"] = move_vals.get("l10n_co_edi_description_code_credit", "1")
        return move_vals
