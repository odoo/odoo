# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PurchaseBillLineMatch(models.Model):
    _inherit = 'purchase.bill.line.match'

    def action_match_lines(self):
        has_posted_bill = any(state == 'posted' for state in self.aml_id.mapped('parent_state'))
        res = super().action_match_lines()
        if has_posted_bill:
            self.pol_id.move_ids.filtered(lambda m: m.is_in or m.is_dropship)._set_value()
        return res
