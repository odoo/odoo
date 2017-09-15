# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockOverProcessedTransfer(models.TransientModel):
    _name = 'stock.overprocessed.transfer'

    picking_id = fields.Many2one('stock.picking')
    overprocessed_products = fields.Many2many('product.product',
                                               compute='_compute_overprocessed_products',
                                               readonly=True)

    @api.multi
    def _compute_overprocessed_products(self):
        for wizard in self:
            wizard.overprocessed_products = wizard.picking_id._get_overprocessed_stock_moves().mapped('product_id')

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        return self.picking_id.with_context(skip_overprocessed_check=True).button_validate()
