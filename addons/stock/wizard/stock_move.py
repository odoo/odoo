# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api
import openerp.addons.decimal_precision as dp

class StockMoveScrap(models.TransientModel):
    _name = "stock.move.scrap"
    _description = "Scrap Products"

    product_id = fields.Many2one('product.product', string='Product', required=True, select=True)
    product_qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one('product.uom', string='Product Unit of Measure', required=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True, default=False)
    restrict_lot_id = fields.Many2one('stock.production.lot', string='Lot')

    @api.model
    def default_get(self, fields):
        """ Get default values
        @param self: The object pointer.
        @return: default values of fields
        """
        res = super(StockMoveScrap, self).default_get(fields)
        move = self.env['stock.move'].browse(self._context['active_id'])
        scrap_location = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1)

        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'location_id' in fields:
            if scrap_location:
                res.update({'location_id': scrap_location.id})
            else:
                res.update({'location_id': False})
        return res

    @api.multi
    def move_scrap(self):
        """ To move scrapped products
        @param self: The object pointer.
        @return:
        """
        move = self.env['stock.move'].browse(self._context['active_id'])
        for record in self:
            move.action_scrap(record.product_qty, record.location_id.id, restrict_lot_id=record.restrict_lot_id.id)
        if move:
            if move.picking_id:
                return {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.picking',
                    'type': 'ir.actions.act_window',
                    'res_id': move.picking_id.id,
                    'context': self._context
                }
        return {'type': 'ir.actions.act_window_close'}
