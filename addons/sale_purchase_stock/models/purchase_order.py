# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.move_dest_ids.group_id.sale_id', 'order_line.move_ids.move_dest_ids.group_id.sale_id')
    def _compute_sale_order_count(self):
        super(PurchaseOrder, self)._compute_sale_order_count()

    def _get_sale_orders(self):
        return super()._get_sale_orders() \
            | self.order_line.move_dest_ids.group_id.sale_id \
            | self.env['stock.move'].browse(self.order_line.move_ids._rollup_move_dests()).group_id.sale_id
