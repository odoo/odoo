# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def read_converted(self):
        result = super().read_converted()
        for sale_line in result:
            gift_card = self.env['sale.order.line'].browse(sale_line['id']).gift_card_id
            if gift_card:
                sale_line['gift_card_id'] = gift_card.id

        return result
