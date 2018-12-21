# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero


class MrpAbstractWorkorder(models.AbstractModel):
    _name = "mrp.abstract.workorder"
    _description = "Common code between produce wizards and workorders."

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', required=True)
    product_id = fields.Many2one(related='production_id.product_id', readonly=True, store=True)
    qty_producing = fields.Float(string='Currently Produced Quantity', digits=dp.get_precision('Product Unit of Measure'))
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, readonly=True)
    final_lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number', domain="[('product_id', '=', product_id)]")
    product_tracking = fields.Selection(related="product_id.tracking")

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        line_values = self._update_workorder_lines()
        for vals in line_values['to_create']:
            self.workorder_line_ids |= self.workorder_line_ids.new(vals)
        if line_values['to_delete']:
            self.workorder_line_ids -= line_values['to_delete']
        for line, vals in line_values['to_update'].items():
            line.update(vals)

    def _update_workorder_lines(self):
        """ Update workorder lines, according to the new qty currently
        produced. It returns a dict with line to create, update or delete.
        It do not directly write or unlink the line because this function is
        used in onchange and request that write on db (e.g. workorder creation).
        """
        line_values = {'to_create': [], 'to_delete': [], 'to_update': {}}
        for move_raw in self.move_raw_ids.filtered(lambda move: move.state not in ('done', 'cancel')):
            move_workorder_lines = self.workorder_line_ids.filtered(lambda w: w.move_id == move_raw)

            # Compute the new quantity for the current component
            rounding = move_raw.product_uom.rounding
            new_qty = self.product_uom_id._compute_quantity(
                self.qty_producing * move_raw.unit_factor,
                self.production_id.product_uom_id,
                round=False
            )
            qty_todo = float_round(new_qty - sum(move_workorder_lines.mapped('qty_done')), precision_rounding=rounding)

            # Remove or lower quantity on exisiting workorder lines
            if float_compare(qty_todo, 0.0, precision_rounding=rounding) < 0:
                qty_todo = abs(qty_todo)
                for workorder_line in move_workorder_lines:
                    if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                        break
                    if float_compare(workorder_line.qty_to_consume, qty_todo, precision_rounding=rounding) <= 0:
                        # update qty_todo for next wo_line
                        qty_todo = float_round(qty_todo - workorder_line.qty_to_consume, precision_rounding=rounding)
                        if line_values['to_delete']:
                            line_values['to_delete'] |= workorder_line
                        else:
                            line_values['to_delete'] = workorder_line
                    else:
                        new_val = workorder_line.qty_to_consume - qty_todo
                        line_values['to_update'][workorder_line] = {
                            'qty_to_consume': new_val,
                            'qty_done': new_val,
                            'qty_reserved': new_val,
                        }
                        qty_todo = 0
            else:
                # Search among wo lines which one could be updated
                for move_line in move_raw.move_line_ids:
                    # Get workorder lines that match reservation.
                    candidates = move_workorder_lines._find_candidate(move_line)
                    while candidates:
                        if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                            break
                        candidate = candidates.pop()
                        qty_to_add = move_line.product_uom_qty - candidate.qty_done
                        line_values['to_update'][candidate] = {
                            'qty_done': candidate.qty_done + qty_to_add,
                            'qty_to_consume': candidate.qty_to_consume + qty_to_add,
                            'qty_reserved': candidate.qty_reserved + qty_to_add,
                        }
                        qty_todo -= qty_to_add

                # if there are still qty_todo, create new wo lines
                if float_compare(qty_todo, 0.0, precision_rounding=rounding) > 0:
                    for vals in self._generate_lines_values(move_raw, qty_todo):
                        line_values['to_create'].append(vals)
        return line_values

    @api.model
    def _generate_lines_values(self, move, qty_to_consume):
        """ Create workorder line. First generate line based on the reservation,
        in order to match the reservation. If the quantity to consume is greater
        than the reservation quantity then create line with the correct quantity
        to consume but without lot or serial number.
        """
        lines = []
        is_tracked = move.product_id.tracking != 'none'
        for move_line in move.move_line_ids:
            if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) <= 0:
                break
            # move line already 'used' in workorder (from its lot for instance)
            if move_line.lot_produced_id or float_compare(move_line.product_uom_qty, move_line.qty_done, precision_rounding=move.product_uom.rounding) <= 0:
                continue
            # search wo line on which the lot is not fully consumed or other reserved lot
            linked_wo_line = self.workorder_line_ids.filtered(
                lambda line: line.product_id == move_line.product_id and
                line.lot_id == move_line.lot_id
            )
            if linked_wo_line:
                if float_compare(sum(linked_wo_line.mapped('qty_to_consume')), move_line.product_uom_qty, precision_rounding=move.product_uom.rounding) < 0:
                    to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty - sum(linked_wo_line.mapped('qty_to_consume')))
                else:
                    continue
            else:
                to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty)
            line = {
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': is_tracked and move.product_id.uom_id.id or move.product_uom.id,
                'qty_to_consume': to_consume_in_line,
                'qty_reserved': move_line.product_uom_qty,
                'lot_id': move_line.lot_id.id,
                'qty_done': is_tracked and 0 or to_consume_in_line
            }
            lines.append(line)
            qty_to_consume -= to_consume_in_line
        # The move has not reserved the whole quantity so we create new wo lines
        if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
            if move.product_id.tracking == 'serial':
                while float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                    line = {
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_id.uom_id.id,
                        'qty_to_consume': 1,
                        'qty_done': 1,
                    }
                    lines.append(line)
                    qty_to_consume -= 1
            else:
                line = {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'qty_to_consume': qty_to_consume,
                    'qty_done': is_tracked and 0 or qty_to_consume
                }
                lines.append(line)
        return lines

    def _update_finished_move(self):
        """ Update the finished move & move lines in order to set the finished
        product lot on it as well as the produced quantity. This method get the
        information either from the last workorder or from the Produce wizard."""
        production_move = self.production_id.move_finished_ids.filtered(
            lambda move: move.product_id == self.product_id and
            move.state not in ('done', 'cancel')
        )
        if production_move and production_move.product_id.tracking != 'none':
            if not self.final_lot_id:
                raise UserError(_('You need to provide a lot for the finished product.'))
            move_line = production_move.move_line_ids.filtered(
                lambda line: line.lot_id.id == self.final_lot_id.id
            )
            if move_line:
                if self.product_id.tracking == 'serial':
                    raise UserError(_('You cannot produce the same serial number twice.'))
                move_line.product_uom_qty += self.qty_producing
                move_line.qty_done += self.qty_producing
            else:
                move_line.create({
                    'move_id': production_move.id,
                    'product_id': production_move.product_id.id,
                    'lot_id': self.final_lot_id.id,
                    'product_uom_qty': self.qty_producing,
                    'product_uom_id': self.product_uom_id.id,
                    'qty_done': self.qty_producing,
                    'location_id': production_move.location_id.id,
                    'location_dest_id': production_move.location_dest_id.id,
                })
        else:
            rounding = production_move.product_uom.rounding
            production_move._set_quantity_done(
                production_move.quantity_done + float_round(self.qty_producing, precision_rounding=rounding)
            )

    def _update_raw_moves(self):
        """ Once the production is done, the lots written on workorder lines
        are saved on stock move lines"""
        vals_list = []
        workorder_lines_to_process = self.workorder_line_ids.filtered(lambda line: line.qty_done > 0)
        for line in workorder_lines_to_process:
            line._update_move_lines()
            if float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding) > 0:
                vals_list += line._create_extra_move_lines()

        self.workorder_line_ids.unlink()
        self.env['stock.move.line'].create(vals_list)


class MrpAbstractWorkorderLine(models.AbstractModel):
    _name = "mrp.abstract.workorder.line"
    _description = "Abstract model to implement product_produce_line as well as\
    workorder_line"

    move_id = fields.Many2one('stock.move')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_tracking = fields.Selection(related="product_id.tracking")
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    qty_to_consume = fields.Float('To Consume', digits=dp.get_precision('Product Unit of Measure'))
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    qty_done = fields.Float('Consumed')
    qty_reserved = fields.Float('Reserved', digits=dp.get_precision('Product Unit of Measure'))

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """ When the user is encoding a produce line for a tracked product, we apply some logic to
        help him. This onchange will automatically switch `qty_done` to 1.0.
        """
        if self.product_id.tracking == 'serial':
            self.qty_done = 1

    @api.onchange('qty_done')
    def _onchange_qty_done(self):
        """ When the user is encoding a produce line for a tracked product, we apply some logic to
        help him. This onchange will warn him if he set `qty_done` to a non-supported value.
        """
        res = {}
        if self.product_id.tracking == 'serial' and not float_is_zero(self.qty_done, self.product_uom_id.rounding):
            if float_compare(self.qty_done, 1.0, precision_rounding=self.product_uom_id.rounding) != 0:
                message = _('You can only process 1.0 %s of products with unique serial number.') % self.product_id.uom_id.name
                res['warning'] = {'title': _('Warning'), 'message': message}
        return res

    def _update_move_lines(self):
        """ update a move line to save the workorder line data"""
        self.ensure_one()
        if self.lot_id:
            move_lines = self.move_id.move_line_ids.filtered(lambda ml: ml.lot_id == self.lot_id and not ml.lot_produced_id)
        else:
            move_lines = self.move_id.move_line_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_produced_id)

        # Sanity check: if the product is a serial number and `lot` is already present in the other
        # consumed move lines, raise.
        if self.product_id.tracking != 'none' and not self.lot_id:
            raise UserError(_('Please enter a lot or serial number for %s !' % self.product_id.display_name))

        if self.lot_id and self.product_id.tracking == 'serial' and self.lot_id in self.move_id.move_line_ids.filtered(lambda ml: ml.qty_done).mapped('lot_id'):
            raise UserError(_('You cannot consume the same serial number twice. Please correct the serial numbers encoded.'))

        # Update reservation and quantity done
        for ml in move_lines:
            rounding = ml.product_uom_id.rounding
            if float_compare(self.qty_done, 0, precision_rounding=rounding) <= 0:
                break
            quantity_to_process = min(self.qty_done, ml.product_uom_qty - ml.qty_done)
            self.qty_done -= quantity_to_process

            new_quantity_done = (ml.qty_done + quantity_to_process)
            # if we produce less than the reserved quantity to produce the finished products
            # in different lots,
            # we create different component_move_lines to record which one was used
            # on which lot of finished product
            if float_compare(new_quantity_done, ml.product_uom_qty, precision_rounding=rounding) >= 0:
                ml.write({
                    'qty_done': new_quantity_done,
                    'lot_produced_id': self._get_final_lot().id
                })
            else:
                new_qty_reserved = ml.product_uom_qty - new_quantity_done
                default = {
                    'product_uom_qty': new_quantity_done,
                    'qty_done': new_quantity_done,
                    'lot_produced_id': self._get_final_lot().id
                }
                ml.copy(default=default)
                ml.with_context(bypass_reservation_update=True).write({
                    'product_uom_qty': new_qty_reserved,
                    'qty_done': 0
                })

    def _create_extra_move_lines(self):
        """Create new sml if quantity produced is bigger than the reserved one"""
        vals_list = []
        quants = self.env['stock.quant']._gather(self.product_id, self.move_id.location_id, lot_id=self.lot_id, strict=False)
        # Search for a sub-locations where the product is available.
        # Loop on the quants to get the locations. If there is not enough
        # quantity into stock, we take the move location. Anyway, no
        # reservation is made, so it is still possible to change it afterwards.
        for quant in quants:
            quantity = quant.reserved_quantity - quant.quantity
            rounding = quant.product_uom_id.rounding
            if (float_compare(quant.quantity, 0, precision_rounding=rounding) <= 0 or
                    float_compare(quantity, 0, precision_rounding=rounding) <= 0):
                continue
            vals = {
                'move_id': self.move_id.id,
                'product_id': self.product_id.id,
                'location_id': quant.location_id.id,
                'location_dest_id': self.move_id.location_dest_id.id,
                'product_uom_qty': 0,
                'product_uom_id': quant.product_uom_id.id,
                'qty_done': min(quantity, self.qty_done),
                'lot_produced_id': self._get_final_lot().id,
            }
            if self.lot_id:
                vals.update({'lot_id': self.lot_id.id})

            vals_list.append(vals)
            self.qty_done -= vals['qty_done']
            # If all the qty_done is distributed, we can close the loop
            if float_compare(self.qty_done, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
                break

        if float_compare(self.qty_done, 0, precision_rounding=self.product_uom_id.rounding) > 0:
            vals = {
                'move_id': self.move_id.id,
                'product_id': self.product_id.id,
                'location_id': self.move_id.location_id.id,
                'location_dest_id': self.move_id.location_dest_id.id,
                'product_uom_qty': 0,
                'product_uom_id': self.product_uom_id.id,
                'qty_done': self.qty_done,
                'lot_produced_id': self._get_final_lot().id,
            }
            if self.lot_id:
                vals.update({'lot_id': self.lot_id.id})

            vals_list.append(vals)

        return vals_list

    def _find_candidate(self, move_line):
        """ Method used in order to return move lines that match reservation.
        The purpose is to update exisiting workorder line regarding the
        reservation of the raw moves.
        """
        rounding = move_line.product_uom_id.rounding
        return self.filtered(lambda line:
            line.lot_id == move_line.lot_id and
            float_compare(line.qty_done, move_line.product_uom_qty, precision_rounding=rounding) < 0 and
            line.product_id == move_line.product_id)

    # To be implemented in specific model
    def _get_final_lot(self):
        raise NotImplementedError('Method _get_final_lot() undefined on %s' % self)

    def _get_production(self):
        raise NotImplementedError('Method _get_production() undefined on %s' % self)
