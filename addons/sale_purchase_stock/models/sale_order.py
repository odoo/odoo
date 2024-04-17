# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('procurement_group_id.stock_move_ids.created_purchase_line_ids.order_id', 'procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id', 'procurement_group_id.group_orig_ids.purchase_order_id')
    def _compute_purchase_order_count(self):
        super(SaleOrder, self)._compute_purchase_order_count()

    def _get_purchase_orders(self):
        mtso_purchase_orders = self._get_mtso_purchase_orders()
        return super()._get_purchase_orders() | self.procurement_group_id.stock_move_ids.created_purchase_line_ids.order_id | self.procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id | mtso_purchase_orders

    def _get_mtso_purchase_orders(self):
        return self.procurement_group_id.group_orig_ids.purchase_order_id

