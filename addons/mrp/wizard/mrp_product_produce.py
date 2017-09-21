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
            serial_finished = (production.product_id.tracking == 'serial')
            if serial_finished:
                todo_quantity = 1.0
            else:
                main_product_moves = production.move_finished_ids.filtered(lambda x: x.product_id.id == production.product_id.id)
                todo_quantity = production.product_qty - sum(main_product_moves.mapped('quantity_done'))
                todo_quantity = todo_quantity if (todo_quantity > 0) else 0
            if 'production_id' in fields:
                res['production_id'] = production.id
            if 'product_id' in fields:
                res['product_id'] = production.product_id.id
            if 'product_uom_id' in fields:
                res['product_uom_id'] = production.product_uom_id.id
            if 'serial' in fields:
                res['serial'] = bool(serial_finished)
            if 'product_qty' in fields:
                res['product_qty'] = todo_quantity
            if 'produce_line_ids' in fields:
                lines = []
                for move in production.move_raw_ids.filtered(lambda x: (x.product_id.tracking != 'none') and x.state not in ('done', 'cancel') and x.bom_line_id):
                    qty_to_consume = todo_quantity / move.bom_line_id.bom_id.product_qty * move.bom_line_id.product_qty
                    for move_line in move.move_line_ids.filtered(lambda ml: not ml.lot_produced_id):
                        if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) < 0:
                            break
                        to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty)
                        lines.append({
                            'move_id': move.id,
                            'qty_to_consume': to_consume_in_line,
                            'qty_done': 0.0,
                            'lot_id': move_line.lot_id.id,
                            'product_uom_id': move.product_uom.id,
                            'product_id': move.product_id.id,
                        })
                        qty_to_consume -= to_consume_in_line
                    if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                        if move.product_id.tracking == 'serial':
                            while float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                                lines.append({
                                    'move_id': move.id,
                                    'qty_to_consume': 1,
                                    'qty_done': 0.0,
                                    'product_uom_id': move.product_uom.id,
                                    'product_id': move.product_id.id,
                                })
                                qty_to_consume -= 1
                        else:
                            lines.append({
                                'move_id': move.id,
                                'qty_to_consume': qty_to_consume,
                                'qty_done': 0.0,
                                'product_uom_id': move.product_uom.id,
                                'product_id': move.product_id.id,
                            })

                res['produce_line_ids'] = [(0, 0, x) for x in lines]
        return res

    serial = fields.Boolean('Requires Serial')
    production_id = fields.Many2one('mrp.production', 'Production')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
    lot_id = fields.Many2one('stock.production.lot', string='Lot')
    produce_line_ids = fields.One2many('mrp.product.produce.line', 'product_produce_id', string='Product to Track')
    product_tracking = fields.Selection(related="product_id.tracking")

    @api.multi
    def do_produce(self):
        # Nothing to do for lots since values are created using default data (stock.move.lots)
        quantity = self.product_qty
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('You should at least produce some quantity'))
        for move in self.production_id.move_raw_ids:
            # TODO currently not possible to guess if the user updated quantity by hand or automatically by the produce wizard.
            if move.product_id.tracking == 'none' and move.quantity_done < move.product_uom_qty and move.state not in ('done', 'cancel') and move.unit_factor:
                rounding = move.product_uom.rounding
                move.quantity_done += float_round(quantity * move.unit_factor, precision_rounding=rounding)
        for move in self.production_id.move_finished_ids:
            if move.product_id.tracking == 'none' and move.state not in ('done', 'cancel'):
                rounding = move.product_uom.rounding
                if move.product_id.id == self.production_id.product_id.id:
                    move.quantity_done += float_round(quantity, precision_rounding=rounding)
                elif move.unit_factor:
                    # byproducts handling
                    move.quantity_done += float_round(quantity * move.unit_factor, precision_rounding=rounding)
        self.check_finished_move_lots()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'state': 'progress',
                'date_start': datetime.now(),
            })
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def check_finished_move_lots(self):
        produce_move = self.production_id.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel'))
        if produce_move and produce_move.product_id.tracking != 'none':
            if not self.lot_id:
                raise UserError(_('You need to provide a lot for the finished product'))
            existing_false_line = produce_move.move_line_ids.filtered(lambda x: not x.lot_id)
            existing_move_line = produce_move.move_line_ids.filtered(lambda x: x.lot_id == self.lot_id)
            if existing_move_line:
                existing_move_line = existing_move_line[0]
                existing_move_line.qty_done += self.product_qty
            elif existing_false_line:
                existing_false_line = existing_false_line[0]
                existing_false_line.qty_done += self.product_qty
                existing_false_line.lot_id = self.lot_id.id
            else:
                vals = {
                  'move_id': produce_move.id,
                  'product_id': produce_move.product_id.id,
                  'production_id': self.production_id.id,
                  'product_uom_qty': 0.0,
                  'product_uom_id': produce_move.product_uom.id,
                  'qty_done': self.product_qty,
                  'lot_id': self.lot_id.id,
                  'location_id': produce_move.location_id.id, 
                  'location_dest_id': produce_move.location_dest_id.id,
                }
                self.env['stock.move.line'].create(vals)

        for pl in self.produce_line_ids:
            if pl.qty_done and pl.lot_id:
                if not pl.move_id:
                    # Find move_id that would match
                    move_id = self.production_id.move_raw_ids.filtered(lambda x: x.product_id == pl.product_id and x.state not in ('done', 'cancel'))
                    if move_id:
                        pl.move_id = move_id
                    else:
                        # create a move and put it in there
                        order = self.production_id
                        pl.move_id = self.env['stock.move'].create({
                                    'name': order.name,
                                    'date': order.date_planned_start,
                                    'date_expected': order.date_planned_start,
                                    'product_id': pl.product_id.id,
                                    'product_uom_qty': 0.0,
                                    'product_uom': pl.product_uom_id.id,
                                    'location_id': order.location_src_id.id,
                                    'location_dest_id': self.product_id.property_stock_production.id,
                                    'raw_material_production_id': order.id,
                                    'company_id': order.company_id.id,
                                    'operation_id': False,
                                    'price_unit': pl.product_id.standard_price,
                                    'procure_method': 'make_to_stock',
                                    'origin': order.name,
                                    'warehouse_id': False,
                                    'group_id': order.procurement_group_id.id,
                                    'propagate': order.propagate,
                                    'unit_factor': 0.0,
                                    'state': 'confirmed'})
                ml = pl.move_id.move_line_ids.filtered(lambda ml: ml.lot_id == pl.lot_id and not ml.lot_produced_id)
                if ml:
                    if (ml.qty_done + pl.qty_done) >= ml.product_uom_qty:
                        ml.write({'qty_done': ml.qty_done + pl.qty_done, 'lot_produced_id': self.lot_id.id})
                    else:
                        new_qty_todo = ml.product_uom_qty - (ml.qty_done + pl.qty_done)
                        default = {'product_uom_qty': ml.qty_done + pl.qty_done,
                                   'qty_done': ml.qty_done + pl.qty_done,
                                   'lot_produced_id': self.lot_id.id}
                        ml.copy(default=default)
                        ml.with_context(bypass_reservation_update=True).write({'product_uom_qty': new_qty_todo, 'qty_done': 0})
                else:
                    self.env['stock.move.line'].create({
                        'move_id': pl.move_id.id,
                        'product_id': pl.product_id.id,
                        'location_id': pl.move_id.location_id.id,
                        'location_dest_id': pl.move_id.location_dest_id.id,
                        'product_uom_qty': 0,
                        'product_uom_id': pl.product_uom_id.id,
                        'qty_done': pl.qty_done,
                        'lot_id': pl.lot_id.id,
                        'lot_produced_id': self.lot_id.id,
                    })
        return True

class MrpProductProduceLine(models.TransientModel):
    _name = "mrp.product.produce.line"
    _description = "Record Production Line"

    product_produce_id = fields.Many2one('mrp.product.produce')
    product_id = fields.Many2one('product.product', 'Product')
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    qty_to_consume = fields.Float('To Consume')
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
    qty_done = fields.Float('Done')
    move_id = fields.Many2one('stock.move')

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if self.product_id.tracking == 'serial':
            self.qty_done = 1
            
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_uom_id = self.product_id.uom_id.id
