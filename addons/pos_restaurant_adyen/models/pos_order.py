# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def set_no_tip(self):
        """Capture the Adyen payment when no tip is set."""
        self.ensure_one()
        payment_line = self.payment_ids.filtered(lambda line: not line.is_change)[0]
        if payment_line.payment_method_id.use_payment_terminal == 'adyen':
            payment_line._adyen_capture_tip()
        return super(PosOrder, self).set_no_tip()
