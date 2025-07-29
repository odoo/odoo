# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = 'pos.payment'

    def _update_payment_line_for_tip(self, tip_amount):
        """Inherit this method to perform reauthorization or capture on electronic payment."""
        self.ensure_one()
        self.write({
            "amount": self.amount + tip_amount,
        })

    @api.constrains('amount')
    def _check_amount(self):
        bypass_check_amount = self.filtered(
            lambda p: p.pos_order_id.state == 'invoiced' and p.pos_order_id.is_tipped
        )
        super(PosConfig, self - bypass_check_amount)._check_amount()
