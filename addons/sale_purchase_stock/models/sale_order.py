# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('stock_reference_ids', 'stock_reference_ids.purchase_ids')
    def _compute_purchase_order_count(self):
        super()._compute_purchase_order_count()

    def _get_purchase_orders(self):
        return super()._get_purchase_orders() | self.stock_reference_ids.purchase_ids
