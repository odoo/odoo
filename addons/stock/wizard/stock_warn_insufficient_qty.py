# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare


class StockWarnInsufficientQty(models.AbstractModel):
    _name = 'stock.warn.insufficient.qty'
    _description = 'Warn Insufficient Quantity'

    product_id = fields.Many2one('product.product', 'Product', required=True)
    location_id = fields.Many2one( 'stock.location', 'Location', domain="[('usage', '=', 'internal')]", required=True)
    quant_ids = fields.Many2many('stock.quant', compute='_compute_quant_ids')

    @api.one
    @api.depends('product_id')
    def _compute_quant_ids(self):
        self.quant_ids = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id.usage', '=', 'internal')
        ])

    def action_done(self):
        raise NotImplementedError()


class StockWarnInsufficientQtyScrap(models.TransientModel):
    _name = 'stock.warn.insufficient.qty.scrap'
    _inherit = 'stock.warn.insufficient.qty'
    _description = 'Warn Insufficient Scrap Quantity'

    scrap_id = fields.Many2one('stock.scrap', 'Scrap')

    def action_done(self):
        return self.scrap_id.do_scrap()

    def action_cancel(self):
        # FIXME in master: we should not have created the scrap in a first place
        return self.scrap_id.sudo().unlink()
