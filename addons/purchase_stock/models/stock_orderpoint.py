# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _get_qty_multiple_to_order(self):
        """ Calculates the minimum quantity that can be ordered according to the
        qty of the product packaging.
        """
        if 'buy' in self.rule_ids.mapped('action'):
            purchase_packaging = self.product_id.packaging_ids.filtered('purchase')
            if purchase_packaging:
                return purchase_packaging[0].qty
        return super()._get_qty_multiple_to_order()
