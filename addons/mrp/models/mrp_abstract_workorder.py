# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero


class MrpAbstractWorkorder(models.AbstractModel):
    _name = "mrp.abstract.workorder"
    _description = "Common code between produce wizards and workorders."
    _check_company_auto = True

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', required=True, check_company=True)
    product_id = fields.Many2one(related='production_id.product_id', readonly=True, store=True, check_company=True)
    qty_producing = fields.Float(string='Currently Produced Quantity', digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, readonly=True)
    finished_lot_id = fields.Many2one(
        'stock.production.lot', string='Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    product_tracking = fields.Selection(related="product_id.tracking")
    consumption = fields.Selection([
        ('strict', 'Strict'),
        ('flexible', 'Flexible')],
        required=True,
    )
    use_create_components_lots = fields.Boolean(related="production_id.picking_type_id.use_create_components_lots")
    company_id = fields.Many2one(related='production_id.company_id')

    @api.model
    def _prepare_component_quantity(self, move, qty_producing):
        """ helper that computes quantity to consume (or to create in case of byproduct)
        depending on the quantity producing and the move's unit factor"""
        if move.product_id.tracking == 'serial':
            uom = move.product_id.uom_id
        else:
            uom = move.product_uom
        return move.product_uom._compute_quantity(
            qty_producing * move.unit_factor,
            uom,
            round=False
        )

    def _workorder_line_ids(self):
        self.ensure_one()
        return self.raw_workorder_line_ids | self.finished_workorder_line_ids

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        """ Modify the qty currently producing will modify the existing
        workorder line in order to match the new quantity to consume for each
        component and their reserved quantity.
        """
        if self.qty_producing <= 0:
            raise UserError(_('You have to produce at least one %s.') % self.product_uom_id.name)
        line_values = self._update_workorder_lines()
        for values in line_values['to_create']:
            self.env[self._workorder_line_ids()._name].new(values)
        for line in line_values['to_delete']:
            if line in self.raw_workorder_line_ids:
                self.raw_workorder_line_ids -= line
            else:
                self.finished_workorder_line_ids -= line
        for line, vals in line_values['to_update'].items():
            line.update(vals)

    def _update_workorder_lines(self):
        """ Update workorder lines, according to the new qty currently
        produced. It returns a dict with line to create, update or delete.
        It do not directly write or unlink the line because this function is
        used in onchange and request that write on db (e.g. workorder creation).
        """
        line_values = {'to_create': [], 'to_delete': [], 'to_update': {}}
        # moves are actual records
        move_finished_ids = self.move_finished_ids._origin.filtered(lambda move: move.product_id != self.product_id and move.state not in ('done', 'cancel'))
        move_raw_ids = self.move_raw_ids._origin.filtered(lambda move: move.state not in ('done', 'cancel'))
        for move in move_raw_ids | move_finished_ids:
            move_workorder_lines = self._workorder_line_ids().filtered(lambda w: w.move_id == move)

            # Compute the new quantity for the current component
            rounding = move.product_uom.rounding
            new_qty = self._prepare_component_quantity(move, self.qty_producing)

            # In case the production uom is different than the workorder uom
            # it means the product is serial and production uom is not the reference
            new_qty = self.product_uom_id._compute_quantity(
                new_qty,
                self.production_id.product_uom_id,
                round=False
            )
            qty_todo = float_round(new_qty - sum(move_workorder_lines.mapped('qty_to_consume')), precision_rounding=rounding)

            # Remove or lower quantity on exisiting workorder lines
            if float_compare(qty_todo, 0.0, precision_rounding=rounding) < 0:
                qty_todo = abs(qty_todo)
                # Try to decrease or remove lines that are not reserved and
                # partialy reserved first. A different decrease strategy could
                # be define in _unreserve_order method.
                for workorder_line in move_workorder_lines.sorted(key=lambda wl: wl._unreserve_order()):
                    if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                        break
                    # If the quantity to consume on the line is lower than the
                    # quantity to remove, the line could be remove.
                    if float_compare(workorder_line.qty_to_consume, qty_todo, precision_rounding=rounding) <= 0:
                        qty_todo = float_round(qty_todo - workorder_line.qty_to_consume, precision_rounding=rounding)
                        if line_values['to_delete']:
                            line_values['to_delete'] |= workorder_line
                        else:
                            line_values['to_delete'] = workorder_line
                    # decrease the quantity on the line
                    else:
                        new_val = workorder_line.qty_to_consume - qty_todo
                        # avoid to write a negative reserved quantity
                        new_reserved = max(0, workorder_line.qty_reserved - qty_todo)
                        line_values['to_update'][workorder_line] = {
                            'qty_to_consume': new_val,
                            'qty_done': new_val,
                            'qty_reserved': new_reserved,
                        }
                        qty_todo = 0
            else:
                # Search among wo lines which one could be updated
                qty_reserved_wl = defaultdict(float)
                # Try to update the line with the greater reservation first in
                # order to promote bigger batch.
                for workorder_line in move_workorder_lines.sorted(key=lambda wl: wl.qty_reserved, reverse=True):
                    rounding = workorder_line.product_uom_id.rounding
                    if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                        break
                    move_lines = workorder_line._get_move_lines()
                    qty_reserved_wl[workorder_line.lot_id] += workorder_line.qty_reserved
                    # The reserved quantity according to exisiting move line
                    # already produced (with qty_done set) and other production
                    # lines with the same lot that are currently on production.
                    qty_reserved_remaining = sum(move_lines.mapped('product_uom_qty')) - sum(move_lines.mapped('qty_done')) - qty_reserved_wl[workorder_line.lot_id]
                    if float_compare(qty_reserved_remaining, 0, precision_rounding=rounding) > 0:
                        qty_to_add = min(qty_reserved_remaining, qty_todo)
                        line_values['to_update'][workorder_line] = {
                            'qty_done': workorder_line.qty_to_consume + qty_to_add,
                            'qty_to_consume': workorder_line.qty_to_consume + qty_to_add,
                            'qty_reserved': workorder_line.qty_reserved + qty_to_add,
                        }
                        qty_todo -= qty_to_add
                        qty_reserved_wl[workorder_line.lot_id] += qty_to_add

                    # If a line exists without reservation and without lot. It
                    # means that previous operations could not find any reserved
                    # quantity and created a line without lot prefilled. In this
                    # case, the system will not find an existing move line with
                    # available reservation anymore and will increase this line
                    # instead of creating a new line without lot and reserved
                    # quantities.
                    if not workorder_line.qty_reserved and not workorder_line.lot_id and workorder_line.product_tracking != 'serial':
                        line_values['to_update'][workorder_line] = {
                            'qty_done': workorder_line.qty_to_consume + qty_todo,
                            'qty_to_consume': workorder_line.qty_to_consume + qty_todo,
                        }
                        qty_todo = 0

                # if there are still qty_todo, create new wo lines
                if float_compare(qty_todo, 0.0, precision_rounding=rounding) > 0:
                    for values in self._generate_lines_values(move, qty_todo):
                        line_values['to_create'].append(values)
        return line_values

    @api.model
    def _generate_lines_values(self, move, qty_to_consume):
        """ Create workorder line. First generate line based on the reservation,
        in order to prefill reserved quantity, lot and serial number.
        If the quantity to consume is greater than the reservation quantity then
        create line with the correct quantity to consume but without lot or
        serial number.
        """
        lines = []
        is_tracked = move.product_id.tracking == 'serial'
        if move in self.move_raw_ids._origin:
            # Get the inverse_name (many2one on line) of raw_workorder_line_ids
            initial_line_values = {self.raw_workorder_line_ids._get_raw_workorder_inverse_name(): self.id}
        else:
            # Get the inverse_name (many2one on line) of finished_workorder_line_ids
            initial_line_values = {self.finished_workorder_line_ids._get_finished_workoder_inverse_name(): self.id}
        for move_line in move.move_line_ids:
            line = dict(initial_line_values)
            if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) <= 0:
                break
            # move line already 'used' in workorder (from its lot for instance)
            if move_line.lot_produced_ids or float_compare(move_line.product_uom_qty, move_line.qty_done, precision_rounding=move.product_uom.rounding) <= 0:
                continue
            # search wo line on which the lot is not fully consumed or other reserved lot
            linked_wo_line = self._workorder_line_ids().filtered(
                lambda line: line.move_id == move and
                line.lot_id == move_line.lot_id
            )
            if linked_wo_line:
                if float_compare(sum(linked_wo_line.mapped('qty_to_consume')), move_line.product_uom_qty - move_line.qty_done, precision_rounding=move.product_uom.rounding) < 0:
                    to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty - move_line.qty_done - sum(linked_wo_line.mapped('qty_to_consume')))
                else:
                    continue
            else:
                to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty - move_line.qty_done)
            line.update({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': is_tracked and move.product_id.uom_id.id or move.product_uom.id,
                'qty_to_consume': to_consume_in_line,
                'qty_reserved': to_consume_in_line,
                'lot_id': move_line.lot_id.id,
                'qty_done': to_consume_in_line,
            })
            lines.append(line)
            qty_to_consume -= to_consume_in_line
        # The move has not reserved the whole quantity so we create new wo lines
        if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
            line = dict(initial_line_values)
            if move.product_id.tracking == 'serial':
                while float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                    line.update({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_id.uom_id.id,
                        'qty_to_consume': 1,
                        'qty_done': 1,
                    })
                    lines.append(line)
                    qty_to_consume -= 1
            else:
                line.update({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'qty_to_consume': qty_to_consume,
                    'qty_done': qty_to_consume,
                })
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
        if not production_move:
            return
        if production_move.product_id.tracking != 'none':
            if not self.finished_lot_id:
                raise UserError(_('You need to provide a lot for the finished product.'))
            move_line = production_move.move_line_ids.filtered(
                lambda line: line.lot_id.id == self.finished_lot_id.id
            )
            if move_line:
                if self.product_id.tracking == 'serial':
                    raise UserError(_('You cannot produce the same serial number twice.'))
                move_line.product_uom_qty += self.qty_producing
                move_line.qty_done += self.qty_producing
            else:
                location_dest_id = production_move.location_dest_id._get_putaway_strategy(self.product_id).id or production_move.location_dest_id.id
                move_line.create({
                    'move_id': production_move.id,
                    'product_id': production_move.product_id.id,
                    'lot_id': self.finished_lot_id.id,
                    'product_uom_qty': self.qty_producing,
                    'product_uom_id': self.product_uom_id.id,
                    'qty_done': self.qty_producing,
                    'location_id': production_move.location_id.id,
                    'location_dest_id': location_dest_id,
                })
        else:
            rounding = production_move.product_uom.rounding
            production_move._set_quantity_done(
                float_round(self.qty_producing, precision_rounding=rounding)
            )

    def _update_moves(self):
        """ Once the production is done. Modify the workorder lines into
        stock move line with the registered lot and quantity done.
        """
        # Before writting produce quantities, we ensure they respect the bom strictness
        self._strict_consumption_check()
        vals_list = []
        workorder_lines_to_process = self._workorder_line_ids().filtered(lambda line: line.product_id != self.product_id and line.qty_done > 0)
        for line in workorder_lines_to_process:
            line._update_move_lines()
            if float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding) > 0:
                vals_list += line._create_extra_move_lines()

        self._workorder_line_ids().filtered(lambda line: line.product_id != self.product_id).unlink()
        self.env['stock.move.line'].create(vals_list)

    def _strict_consumption_check(self):
        if self.consumption == 'strict':
            for move in self.move_raw_ids:
                lines = self._workorder_line_ids().filtered(lambda l: l.move_id == move)
                qty_done = 0.0
                qty_to_consume = 0.0
                for line in lines:
                    qty_done += line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)
                    qty_to_consume += line.product_uom_id._compute_quantity(line.qty_to_consume, line.product_id.uom_id)
                rounding = self.product_uom_id.rounding
                if float_compare(qty_done, qty_to_consume, precision_rounding=rounding) != 0:
                    raise UserError(_('You should consume the quantity of %s defined in the BoM. If you want to consume more or less components, change the consumption setting on the BoM.') % lines[0].product_id.name)


class MrpAbstractWorkorderLine(models.AbstractModel):
    _name = "mrp.abstract.workorder.line"
    _description = "Abstract model to implement product_produce_line as well as\
    workorder_line"
    _check_company_auto = True

    move_id = fields.Many2one('stock.move', check_company=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, check_company=True)
    product_tracking = fields.Selection(related="product_id.tracking")
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        check_company=True,
        domain="[('product_id', '=', product_id), '|', ('company_id', '=', False), ('company_id', '=', parent.company_id)]")
    qty_to_consume = fields.Float('To Consume', digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    qty_done = fields.Float('Consumed', digits='Product Unit of Measure')
    qty_reserved = fields.Float('Reserved', digits='Product Unit of Measure')
    company_id = fields.Many2one('res.company', compute='_compute_company_id')

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """ When the user is encoding a produce line for a tracked product, we apply some logic to
        help him. This onchange will automatically switch `qty_done` to 1.0.
        """
        if self.product_id.tracking == 'serial':
            self.qty_done = 1

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and not self.move_id:
            self.product_uom_id = self.product_id.uom_id

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

    def _compute_company_id(self):
        for line in self:
            line.company_id = line._get_production().company_id

    def _update_move_lines(self):
        """ update a move line to save the workorder line data"""
        self.ensure_one()
        if self.lot_id:
            move_lines = self.move_id.move_line_ids.filtered(lambda ml: ml.lot_id == self.lot_id and not ml.lot_produced_ids)
        else:
            move_lines = self.move_id.move_line_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_produced_ids)

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
                    'lot_produced_ids': self._get_produced_lots(),
                })
            else:
                new_qty_reserved = ml.product_uom_qty - new_quantity_done
                default = {
                    'product_uom_qty': new_quantity_done,
                    'qty_done': new_quantity_done,
                    'lot_produced_ids': self._get_produced_lots(),
                }
                ml.copy(default=default)
                ml.with_context(bypass_reservation_update=True).write({
                    'product_uom_qty': new_qty_reserved,
                    'qty_done': 0
                })

    def _create_extra_move_lines(self):
        """Create new sml if quantity produced is bigger than the reserved one"""
        vals_list = []
        # apply putaway
        location_dest_id = self.move_id.location_dest_id._get_putaway_strategy(self.product_id) or self.move_id.location_dest_id
        quants = self.env['stock.quant']._gather(self.product_id, self.move_id.location_id, lot_id=self.lot_id, strict=False)
        # Search for a sub-locations where the product is available.
        # Loop on the quants to get the locations. If there is not enough
        # quantity into stock, we take the move location. Anyway, no
        # reservation is made, so it is still possible to change it afterwards.
        for quant in quants:
            quantity = quant.quantity - quant.reserved_quantity
            quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom_id, rounding_method='HALF-UP')
            rounding = quant.product_uom_id.rounding
            if (float_compare(quant.quantity, 0, precision_rounding=rounding) <= 0 or
                    float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0):
                continue
            vals = {
                'move_id': self.move_id.id,
                'product_id': self.product_id.id,
                'location_id': quant.location_id.id,
                'location_dest_id': location_dest_id.id,
                'product_uom_qty': 0,
                'product_uom_id': self.product_uom_id.id,
                'qty_done': min(quantity, self.qty_done),
                'lot_produced_ids': self._get_produced_lots(),
            }
            if self.lot_id:
                vals.update({'lot_id': self.lot_id.id})

            vals_list.append(vals)
            self.qty_done -= vals['qty_done']
            # If all the qty_done is distributed, we can close the loop
            if float_compare(self.qty_done, 0, precision_rounding=self.product_id.uom_id.rounding) <= 0:
                break

        if float_compare(self.qty_done, 0, precision_rounding=self.product_id.uom_id.rounding) > 0:
            vals = {
                'move_id': self.move_id.id,
                'product_id': self.product_id.id,
                'location_id': self.move_id.location_id.id,
                'location_dest_id': location_dest_id.id,
                'product_uom_qty': 0,
                'product_uom_id': self.product_uom_id.id,
                'qty_done': self.qty_done,
                'lot_produced_ids': self._get_produced_lots(),
            }
            if self.lot_id:
                vals.update({'lot_id': self.lot_id.id})

            vals_list.append(vals)

        return vals_list

    def _unreserve_order(self):
        """ Unreserve line with lower reserved quantity first """
        self.ensure_one()
        return (self.qty_reserved,)

    def _get_move_lines(self):
        return self.move_id.move_line_ids.filtered(lambda ml:
        ml.lot_id == self.lot_id and ml.product_id == self.product_id)

    def _get_produced_lots(self):
        return self.move_id in self._get_production().move_raw_ids and self._get_final_lots() and [(4, lot.id) for lot in self._get_final_lots()]

    @api.model
    def _get_raw_workorder_inverse_name(self):
        raise NotImplementedError('Method _get_raw_workorder_inverse_name() undefined on %s' % self)

    @api.model
    def _get_finished_workoder_inverse_name(self):
        raise NotImplementedError('Method _get_finished_workoder_inverse_name() undefined on %s' % self)

    # To be implemented in specific model
    def _get_final_lots(self):
        raise NotImplementedError('Method _get_final_lots() undefined on %s' % self)

    def _get_production(self):
        raise NotImplementedError('Method _get_production() undefined on %s' % self)
