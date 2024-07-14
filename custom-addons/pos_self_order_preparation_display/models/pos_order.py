# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _send_order(self):
        super()._send_order()
        self.env['pos_preparation_display.order'].sudo().process_order(self.id)

    def write(self, values):
        res = super().write(values)

        for order in self:
            if order.state == 'paid' or values.get('state') == 'paid':
                order._send_order()

        return res
