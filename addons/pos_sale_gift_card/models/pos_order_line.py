# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    @api.model
    def create(self, values):
        if 'sale_order_line_id' in values:
            gift_card = self.env['sale.order.line'].browse(values['sale_order_line_id']).gift_card_id
            #If the giftcard was already in a sale order before loading the order in the PoS, we need to remove the giftcard_id because it would be counted as used 2 times
            if gift_card:
                values['gift_card_id'] = None
        return super(PosOrderLine, self).create(values)
