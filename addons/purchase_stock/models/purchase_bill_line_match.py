# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PurchaseBillLineMatch(models.Model):
    _inherit = 'purchase.bill.line.match'

    def action_match_lines(self):
        # The SQL view only list AMLs unlinked to any pol, so matching them in the super calls might
        # remove their rows from it
        amls = self.aml_id
        res = super().action_match_lines()
        posted_amls = amls.exists().filtered(lambda line: line.parent_state == 'posted')
        posted_amls._get_stock_moves().filtered(lambda m: m.is_in or m.is_dropship)._set_value()
        return res
