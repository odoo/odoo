# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # === ACTION METHODS === #

    def _action_launch_stock_rule(self, **kwargs):
        """ Override of sale_stock to prevent creating pickings for Gelato products. """
        gelato_lines = self.filtered(lambda l: l.product_id.gelato_product_uid)
        super(SaleOrderLine, self - gelato_lines)._action_launch_stock_rule(**kwargs)
