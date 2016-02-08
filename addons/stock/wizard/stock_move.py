# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


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
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: default values of fields
        """
        res = super(StockMoveScrap, self).default_get(fields)
        move = self.env['stock.move'].browse(self.env.context.get('active_id', []))

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
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        move = self.env['stock.move'].browse(self.env.context.get('active_ids'))
        for data in self:
            move.action_scrap(data.product_qty, data.location_id.id, restrict_lot_id=data.restrict_lot_id.id)
        if move:
            if move.picking_id:
                return {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.picking',
                    'type': 'ir.actions.act_window',
                    'res_id': move.picking_id.id,
                    'context': self.env.context
                }
        return {'type': 'ir.actions.act_window_close'}
