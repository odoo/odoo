# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_valued_in_moves(self):
        self.ensure_one()
        return self.purchase_line_id.move_ids.filtered(lambda m: m._is_in())

    def _is_not_eligible_for_price_difference(self):
        self.ensure_one()
        return self.product_id.type != 'product' or self.product_id.valuation != 'real_time'
