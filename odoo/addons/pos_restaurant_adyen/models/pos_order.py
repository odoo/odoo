# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        if not self.config_id.set_tip_after_payment:
            payment_lines = self.payment_ids.filtered(lambda line: line.payment_method_id.use_payment_terminal == 'adyen')
            for payment_line in payment_lines:
                payment_line._adyen_capture()
        return res
