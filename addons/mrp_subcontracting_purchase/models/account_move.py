# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_get_last_step_stock_moves(self):
        rslt = super()._stock_account_get_last_step_stock_moves()
        subcontracted_moves = self.filtered(lambda m: m.move_type == 'in_invoice').invoice_line_ids.purchase_line_id.move_ids.filtered(
            lambda m: m.state == 'done' and m.is_subcontract)
        # subcontracted move valuations are not linked to the PO move but its orig move (the MO finished move)
        return rslt | subcontracted_moves | subcontracted_moves.move_orig_ids
