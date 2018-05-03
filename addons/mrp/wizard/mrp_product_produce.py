# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from datetime import datetime

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
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
                    qty_to_consume = float_round(todo_quantity / move.bom_line_id.bom_id.product_qty * move.bom_line_id.product_qty,
                                                 precision_rounding=move.product_uom.rounding, rounding_method="UP")
                    for move_line in move.move_line_ids:
                        if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) <= 0:
                            break
                        if move_line.lot_produced_id or float_compare(move_line.product_uom_qty, move_line.qty_done, precision_rounding=move.product_uom.rounding) <= 0:
                            continue
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
            raise UserError(_("The production order for '%s' has no quantity specified") % self.product_id.display_name)
        for move in self.production_id.move_raw_ids:
            # TODO currently not possible to guess if the user updated quantity by hand or automatically by the produce wizard.
            if move.product_id.tracking == 'none' and move.state not in ('done', 'cancel') and move.unit_factor:
                rounding = move.product_uom.rounding
                if self.product_id.tracking != 'none':
                    qty_to_add = float_round(quantity * move.unit_factor, precision_rounding=rounding)
                    move._generate_consumed_move_line(qty_to_add, self.lot_id)
                else:
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
            existing_move_line = produce_move.move_line_ids.filtered(lambda x: x.lot_id == self.lot_id)
            if existing_move_line:
                if self.product_id.tracking == 'serial':
                    raise UserError(_('You cannot produce the same serial number twice.'))
                existing_move_line.product_uom_qty += self.product_qty
                existing_move_line.qty_done += self.product_qty
            else:
                vals = {
                  'move_id': produce_move.id,
                  'product_id': produce_move.product_id.id,
                  'production_id': self.production_id.id,
                  'product_uom_qty': self.product_qty,
                  'product_uom_id': produce_move.product_uom.id,
                  'qty_done': self.product_qty,
                  'lot_id': self.lot_id.id,
                  'location_id': produce_move.location_id.id,
                  'location_dest_id': produce_move.location_dest_id.id,
                }
                self.env['stock.move.line'].create(vals)

        for pl in self.produce_line_ids:
            if pl.qty_done:
                if not pl.lot_id:
                    raise UserError(_('Please enter a lot or serial number for %s !' % pl.product_id.name))
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
                                    'product_id': pl.product_id.id,
                                    'product_uom': pl.product_uom_id.id,
                                    'location_id': order.location_src_id.id,
                                    'location_dest_id': self.product_id.property_stock_production.id,
                                    'raw_material_production_id': order.id,
                                    'group_id': order.procurement_group_id.id,
                                    'origin': order.name,
                                    'state': 'confirmed'})
                pl.move_id._generate_consumed_move_line(pl.qty_done, self.lot_id, lot=pl.lot_id)
        return True


class MrpProductProduceLine(models.TransientModel):
    _name = "mrp.product.produce.line"
    _description = "Record Production Line"

    product_produce_id = fields.Many2one('mrp.product.produce')
    product_id = fields.Many2one('product.product', 'Product')
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    qty_to_consume = fields.Float('To Consume', digits=dp.get_precision('Product Unit of Measure'))
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
    qty_done = fields.Float('Done', digits=dp.get_precision('Product Unit of Measure'))
    move_id = fields.Many2one('stock.move')

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """ When the user is encoding a produce line for a tracked product, we apply some logic to
        help him. This onchange will automatically switch `qty_done` to 1.0.
        """
        res = {}
        if self.product_id.tracking == 'serial':
            self.qty_done = 1
        return res

    @api.onchange('qty_done')
    def _onchange_qty_done(self):
        """ When the user is encoding a produce line for a tracked product, we apply some logic to
        help him. This onchange will warn him if he set `qty_done` to a non-supported value.
        """
        res = {}
        if self.product_id.tracking == 'serial':
            if float_compare(self.qty_done, 1.0, precision_rounding=self.move_id.product_id.uom_id.rounding) != 0:
                message = _('You can only process 1.0 %s for products with unique serial number.') % self.product_id.uom_id.name
                res['warning'] = {'title': _('Warning'), 'message': message}
        return res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_uom_id = self.product_id.uom_id.id
