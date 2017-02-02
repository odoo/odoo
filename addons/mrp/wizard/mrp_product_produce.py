# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round

class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Record Production"

    @api.model
    def default_get(self, fields):
        res = super(MrpProductProduce, self).default_get(fields)
        if self._context and self._context.get('active_id'):
            production = self.env['mrp.production'].browse(self._context['active_id'])
            #serial_raw = production.move_raw_ids.filtered(lambda x: x.product_id.tracking == 'serial')
            main_product_moves = production.move_finished_ids.filtered(lambda x: x.product_id.id == production.product_id.id)
            serial_finished = (production.product_id.tracking == 'serial')
            serial = bool(serial_finished)
            if serial_finished:
                quantity = 1.0
            else:
                quantity = production.product_qty - sum(main_product_moves.mapped('quantity_done'))
                quantity = quantity if (quantity > 0) else 0
            lines = []
            existing_lines = []
            for move in production.move_raw_ids.filtered(lambda x: (x.product_id.tracking != 'none') and x.state not in ('done', 'cancel')):
                if not move.move_lot_ids:
                    qty = quantity / move.bom_line_id.bom_id.product_qty * move.bom_line_id.product_qty
                    if move.product_id.tracking == 'serial':
                        while float_compare(qty, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                            lines.append({
                                'move_id': move.id,
                                'quantity': min(1,qty),
                                'quantity_done': 0.0,
                                'plus_visible': True,
                                'product_id': move.product_id.id,
                                'production_id': production.id,
                            })
                            qty -= 1
                    else:
                        lines.append({
                            'move_id': move.id,
                            'quantity': qty,
                            'quantity_done': 0.0,
                            'plus_visible': True,
                            'product_id': move.product_id.id,
                            'production_id': production.id,
                        })
                else:
                    existing_lines += move.move_lot_ids.filtered(lambda x: not x.lot_produced_id).ids

            res['serial'] = serial
            res['production_id'] = production.id
            res['product_qty'] = quantity
            res['product_id'] = production.product_id.id
            res['product_uom_id'] = production.product_uom_id.id
            res['consume_line_ids'] = map(lambda x: (0,0,x), lines) + map(lambda x:(4, x), existing_lines)
        return res

    serial = fields.Boolean('Requires Serial')
    production_id = fields.Many2one('mrp.production', 'Production')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
    lot_id = fields.Many2one('stock.production.lot', string='Lot')
    consume_line_ids = fields.Many2many('stock.move.lots', 'mrp_produce_stock_move_lots', string='Product to Track')
    product_tracking = fields.Selection(related="product_id.tracking")

    @api.multi
    def do_produce(self):
        # Nothing to do for lots since values are created using default data (stock.move.lots)
        moves = self.production_id.move_raw_ids
        quantity = self.product_qty
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('You should at least produce some quantity'))
        for move in moves.filtered(lambda x: x.product_id.tracking == 'none' and x.state not in ('done', 'cancel')):
            if move.unit_factor:
                rounding = move.product_uom.rounding
                move.quantity_done_store += float_round(quantity * move.unit_factor, precision_rounding=rounding)
        moves = self.production_id.move_finished_ids.filtered(lambda x: x.product_id.tracking == 'none' and x.state not in ('done', 'cancel'))
        for move in moves:
            rounding = move.product_uom.rounding
            if move.product_id.id == self.production_id.product_id.id:
                move.quantity_done_store += float_round(quantity, precision_rounding=rounding)
            elif move.unit_factor:
                # byproducts handling
                move.quantity_done_store += float_round(quantity * move.unit_factor, precision_rounding=rounding)
        self.check_finished_move_lots()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'state': 'progress',
                'date_start': datetime.now(),
            })
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def check_finished_move_lots(self):
        lots = self.env['stock.move.lots']
        produce_move = self.production_id.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel'))
        if produce_move.product_id.tracking != 'none':
            if not self.lot_id:
                raise UserError(_('You need to provide a lot for the finished product'))
            existing_move_lot = produce_move.move_lot_ids.filtered(lambda x: x.lot_id == self.lot_id)
            if existing_move_lot:
                existing_move_lot.quantity += self.product_qty
                existing_move_lot.quantity_done += self.product_qty
            else:
                vals = {
                  'move_id': produce_move.id,
                  'product_id': produce_move.product_id.id,
                  'production_id': self.production_id.id,
                  'quantity': self.product_qty,
                  'quantity_done': self.product_qty,
                  'lot_id': self.lot_id.id,
                }
                lots.create(vals)
            for move in self.production_id.move_raw_ids:
                for movelots in move.move_lot_ids.filtered(lambda x: not x.lot_produced_id):
                    if movelots.quantity_done and self.lot_id:
                        #Possibly the entire move is selected
                        remaining_qty = movelots.quantity - movelots.quantity_done
                        if remaining_qty > 0:
                            new_move_lot = movelots.copy()
                            new_move_lot.write({'quantity':movelots.quantity_done, 'lot_produced_id': self.lot_id.id})
                            movelots.write({'quantity': remaining_qty, 'quantity_done': 0})
                        else:
                            movelots.write({'lot_produced_id': self.lot_id.id})
        return True
