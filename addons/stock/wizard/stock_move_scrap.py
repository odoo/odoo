# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class ScrapProduct(models.TransientModel):
    _name = "stock.move.scrap"
    _description = "Scrap Products"

    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure', required=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    restrict_lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')

    @api.model
    def default_get(self, fields):
        res = super(ScrapProduct, self).default_get(fields)
        Move = self.env['stock.move']
        if self.env.context.get('active_id'):
            move = Move.browse(self.env.context['active_id'])
        else:
            move = Move
        if 'product_id' in fields and not res.get('product_id') and move:
            res['product_id'] = move.product_id.id
        if 'product_uom' in fields and not res.get('productr_uom') and move:
            res['product_uom'] = move.product_uom.id
        if 'location_id' in fields and not res.get('location_id'):
            scrap_location = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1)
            res['location_id'] = scrap_location.id
        return res

    @api.multi
    def move_scrap(self):
        moves = self.env['stock.move'].browse(self.env.context.get('active_ids', list()))
        for wizard in self:
            moves.action_scrap(wizard.product_qty, wizard.location_id.id, restrict_lot_id=wizard.restrict_lot_id.id)
        move = moves and moves[0] or False
        if move and move.picking_id:
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': move.picking_id.id,
                'context': self.env.context
            }
        return {'type': 'ir.actions.act_window_close'}
