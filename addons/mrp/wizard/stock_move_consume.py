# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare
from odoo.addons import decimal_precision as dp


class StockMoveConsume(models.TransientModel):
    _name = "stock.move.consume"
    _description = "Consume Products"

    product_id = fields.Many2one(
        'product.product', 'Product',
        index=True, required=True)
    product_qty = fields.Float(
        'Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        required=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        required=True)
    restrict_lot_id = fields.Many2one(
        'stock.production.lot', 'Lot')

    # TOFIX: product_uom should not have different category of default UOM of product. Qty should be convert into UOM of original move line before going in consume and scrap
    def default_get(self, fields):
        res = super(StockMoveConsume, self).default_get(fields)
        move = self.env['stock.move'].browse(self._context['active_id'])
        if 'product_id' in fields:
            res['product_id'] = move.product_id.id
        if 'product_uom' in fields:
            res['product_uom'] = move.product_uom.id
        if 'product_qty' in fields:
            res['product_qty'] = move.product_uom_qty
        if 'location_id' in fields:
            res['location_id'] = move.location_id.id
        return res

    @api.multi
    def do_move_consume(self):
        Production = self.env['mrp.production']

        move = self.env['stock.move'].browse(self._context['active_id'])
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for wizard in self:
            qty = wizard.product_uom._compute_quantity(wizard.product_qty, wizard.product_id.uom_id)
            remaining_qty = move.product_qty - qty
            # check for product quantity is less than previously planned
            if float_compare(remaining_qty, 0, precision_digits=precision) >= 0:
                move.action_consume(qty, wizard.location_id.id, restrict_lot_id=wizard.restrict_lot_id.id)
            else:
                consumed_qty = min(move.product_qty, qty)
                move.action_consume(consumed_qty, wizard.location_id.id, restrict_lot_id=wizard.restrict_lot_id.id)
                # consumed more in wizard than previously planned
                extra_more_qty = qty - consumed_qty
                # create new line for a remaining qty of the product
                extra_move = Production._make_consume_line_from_data(move.raw_material_production_id, wizard.product_id, wizard.product_id.uom_id.id, extra_more_qty)
                extra_move.write({'restrict_lot_id': wizard.restrict_lot_id.id})
                extra_move.action_done()
        return {'type': 'ir.actions.act_window_close'}
