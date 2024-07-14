# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class PosOrder(models.Model):
    _inherit = "pos.order"

    def _process_order(self, order, draft, existing_order):
        order_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        order = self.browse(order_id)
        for line in order.lines:
            if line.sale_order_line_id and line.product_id.rent_ok and line.product_id.tracking != 'none':
                line.sale_order_line_id.pickedup_lot_ids = self.env['stock.lot'].search([('name', 'in', line.pack_lot_ids.mapped('lot_name')), ('product_id', '=', line.product_id.id)])
        return order_id
