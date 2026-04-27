# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.misc import groupby as tools_groupby


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tracking = fields.Selection(related='product_id.tracking', depends=['product_id'])

    reserved_lot_ids = fields.Many2many('stock.lot', 'rental_reserved_lot_rel', domain="[('product_id','=',product_id)]", copy=False)
    pickedup_lot_ids = fields.Many2many('stock.lot', 'rental_pickedup_lot_rel', domain="[('product_id','=',product_id)]", copy=False)
    returned_lot_ids = fields.Many2many('stock.lot', 'rental_returned_lot_rel', domain="[('product_id','=',product_id)]", copy=False)

    unavailable_lot_ids = fields.Many2many('stock.lot', 'unreturned_reserved_serial', compute='_compute_unavailable_lots', store=False)
    available_reserved_lots = fields.Boolean(compute='_compute_available_reserved_lots')

    @api.depends('reserved_lot_ids', 'reservation_begin', 'return_date')
    def _compute_available_reserved_lots(self):
        # A lot is available if it is currently in the stock AND it won't be removed from stock
        # before the end of rental period.
        # A lot is available if it is not currently in the stock AND it will be back in stock
        # before the start of rental period.
        self.available_reserved_lots = True
        if not self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            return
        lines_to_check = self.filtered(lambda l: l.is_rental and l.reserved_lot_ids and l.product_template_id.tracking == 'serial')

        partner_location_id = self.env.ref('stock.stock_location_locations_partner')

        for line in lines_to_check:
            company_id = line.order_id.company_id.id
            domain = [
                ('company_id', '=', company_id),
                ('state', 'not in', ['done', 'cancel']),
                ('lot_id', 'in', line.reserved_lot_ids.ids),
            ]
            leaving_move_lines_groups = self.env['stock.move.line']._read_group(
                expression.AND([domain, [
                            ('location_usage', '=', 'internal'),
                            ('location_dest_id', 'child_of', partner_location_id.id),
                        ]]),
                groupby=['lot_id'],
                aggregates=['id:recordset'],
            )
            leaving_move_by_lot = {g[0].id: g[1] for g in leaving_move_lines_groups}
            incoming_move_lines_groups = self.env['stock.move.line']._read_group(
                expression.AND([domain, [
                            ('location_id', 'child_of', partner_location_id.id),
                            ('location_dest_usage', '=', 'internal'),
                        ]]),
                groupby=['lot_id'],
                aggregates=['id:recordset'],
            )
            incoming_move_by_lot = {g[0].id: g[1] for g in incoming_move_lines_groups}
            for lot in line.reserved_lot_ids:
                lot_id = lot.ids[0]
                if lot_id in line.move_ids.lot_ids.ids:
                    continue
                in_stock = bool(sum(
                    lot.quant_ids.filtered(
                        lambda q: q.location_id.usage in ['internal', 'transit']
                            and q.location_id not in partner_location_id.child_internal_location_ids
                            and q.company_id.id == company_id).mapped('quantity')
                    ))
                if in_stock:
                    leaving_move_line = leaving_move_by_lot.get(lot_id, False)
                    leaving = bool(leaving_move_line and (
                        leaving_move_line.move_id.date_deadline <= line.return_date
                        and not (
                            # will return in time from an other renting
                            leaving_move_line.move_id.sale_line_id.return_date
                            and leaving_move_line.move_id.sale_line_id.return_date <= line.reservation_begin
                        ))
                    )
                    in_stock = not leaving
                else:
                    incoming_move_line = incoming_move_by_lot.get(lot_id, False)
                    incoming = bool(incoming_move_line and incoming_move_line.move_id.date_deadline <= line.reservation_begin)
                    in_stock = incoming
                if not in_stock:
                    line.available_reserved_lots = False
                    break

    def _partition_so_lines_by_rental_period(self):
        """ Return a partition of sale.order.line based on (from_date, to_date, warehouse_id)
        """
        now = fields.Datetime.now()
        lines_grouping_key = {
            line.id: (line.reservation_begin, line.return_date, line.order_id.warehouse_id.id)
            for line in self
        }
        keyfunc = lambda line_id: (max(lines_grouping_key[line_id][0], now), lines_grouping_key[line_id][1], lines_grouping_key[line_id][2])
        return tools_groupby(self._ids, key=keyfunc)

    @api.depends('reservation_begin', 'return_date', 'product_id')
    def _compute_qty_at_date(self):
        non_rental = self.filtered(lambda sol: not sol.is_rental)
        super(RentalOrderLine, non_rental)._compute_qty_at_date()
        rented_product_lines = (self - non_rental).filtered(
            lambda l: l.product_id and l.product_id.is_storable
        )
        line_default_values = {
            'virtual_available_at_date': 0.0,
            'scheduled_date': False,
            'forecast_expected_date': False,
            'free_qty_today': 0.0,
            'qty_available_today': False,
        }
        for (from_date, to_date, warehouse_id), line_ids in rented_product_lines._partition_so_lines_by_rental_period():
            lines = self.env['sale.order.line'].browse(line_ids)
            for line in lines:
                if from_date <= fields.Datetime.now():
                    rentable_qty = line.product_id.with_context(
                        from_date=from_date,
                        to_date=to_date,
                        warehouse_id=warehouse_id).qty_available
                else:
                    # For performance reason it is not reasonable to find the minimal forecasted quantity
                    # during the rental period so that we fallback on the forecasted quantity at the
                    # first day of the rental period.
                    rentable_qty = line.product_id.with_context(
                        from_date=False,
                        to_date=from_date,
                        warehouse_id=warehouse_id).virtual_available
                    # The rented_qty_during_period can overlap with planned
                    # incoming/outgoing moves taken into account by the virtual_available qty
                    rentable_qty += line.product_id._get_virtual_unavailable_qty_in_rent(
                        pivot_date=from_date,
                        ignored_soline_id=line and line.state == 'draft' and line.id,
                        warehouse_id=line.order_id.warehouse_id.id,
                    )
                rented_qty_during_period = line.product_id._get_unavailable_qty(
                    from_date, to_date,
                    ignored_soline_id=line and line.id,
                    warehouse_id=line.order_id.warehouse_id.id,
                )
                virtual_available_at_date = max(rentable_qty - rented_qty_during_period, 0)
                line.update(dict(line_default_values,
                    virtual_available_at_date=virtual_available_at_date,
                    scheduled_date=from_date,
                    free_qty_today=virtual_available_at_date)
                )
        ((self - non_rental) - rented_product_lines).update(line_default_values)

    @api.depends('is_rental')
    def _compute_qty_delivered_method(self):
        """Allow modification of delivered qty without depending on stock moves."""
        rental_lines = self.filtered('is_rental')
        super(RentalOrderLine, self - rental_lines)._compute_qty_delivered_method()
        rental_lines.qty_delivered_method = 'manual'

    def write(self, vals):
        """Move product quantities on pickup/return in case of rental orders.

        When qty_delivered or qty_returned are changed (and/or pickedup_lot_ids/returned_lot_ids),
        we need to move those quants to make sure they aren't seen as available in the stock.
        For quantities, the quantity is requested in the warehouse (self.order_id.warehouse_id) through stock move generation.
        For serial numbers(lots), lots are found one by one and then a stock move is generated based on the quant location itself.

        The destination location is the independent internal location of the company dedicated to stock in rental, to still count
        in inventory valuation and company assets.

        When quantity/lots are decreased/removed, we decrease the quantity in the stock moves made by previous corresponding write call.
        """
        if not any(key in vals for key in ['qty_delivered', 'pickedup_lot_ids', 'qty_returned', 'returned_lot_ids']) or self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            # If nothing to catch for rental: usual write behavior
            return super(RentalOrderLine, self).write(vals)

        # TODO add context for disabling stock moves in write ?
        old_vals = dict()
        movable_confirmed_rental_lines = self.filtered(
            lambda sol: sol.is_rental
                and sol.state == 'sale'
                and sol.product_id.type == "consu")
        for sol in movable_confirmed_rental_lines:
            old_vals[sol.id] = (sol.pickedup_lot_ids, sol.returned_lot_ids) if sol.product_id.tracking == 'serial' else (sol.qty_delivered, sol.qty_returned)
            if vals.get('pickedup_lot_ids', False) and vals['pickedup_lot_ids'][0][0] == 6:
                pickedup_lot_ids = vals['pickedup_lot_ids'][0][2]
                if sol.product_uom_qty == len(pickedup_lot_ids) and pickedup_lot_ids != sol.reserved_lot_ids.ids:
                    """ When setting the pickedup_lots:
                    If the total reserved quantity is picked_up we need to unreserve
                    the reserved_lots not picked to ensure the consistency of rental reservations.
                    NOTE: This is only guaranteed for generic 6, _, _ orm magic commands.
                    """
                    vals['reserved_lot_ids'] = vals['pickedup_lot_ids']

        res = super(RentalOrderLine, self).write(vals)

        self._write_rental_lines(movable_confirmed_rental_lines, old_vals, vals)
        # TODO constraint s.t. qty_returned cannot be > than qty_delivered (and same for lots)
        return res

    def _write_rental_lines(self, lines, old_vals, vals):
        if not lines:
            return

        lines.mapped('company_id').filtered(lambda company: not company.rental_loc_id)._create_rental_location()
        # to undo stock moves partially: what if location has changed? :x
        # can we ascertain the warehouse_id.lot_stock_id of a sale.order doesn't change???

        for sol in lines:
            sol = sol.with_company(sol.company_id)
            rented_location = sol.company_id.rental_loc_id
            stock_location = sol.order_id.warehouse_id.lot_stock_id
            if sol.product_id.tracking == 'serial' and (vals.get('pickedup_lot_ids', False) or vals.get('returned_lot_ids', False)):
                # for product tracked by serial numbers: move the lots
                if vals.get('pickedup_lot_ids', False):
                    pickedup_lots = sol.pickedup_lot_ids - old_vals[sol.id][0]
                    removed_pickedup_lots = old_vals[sol.id][0] - sol.pickedup_lot_ids
                    sol._move_serials(pickedup_lots, stock_location, rented_location)
                    sol._return_serials(removed_pickedup_lots, rented_location, stock_location)
                if vals.get('returned_lot_ids', False):
                    returned_lots = sol.returned_lot_ids - old_vals[sol.id][1]
                    removed_returned_lots = old_vals[sol.id][1] - sol.returned_lot_ids
                    sol._move_serials(returned_lots, rented_location, stock_location)
                    sol._return_serials(removed_returned_lots, stock_location, rented_location)
            elif sol.product_id.tracking != 'serial' and any(k in vals for k in ('qty_delivered', 'qty_returned')):
                # for products not tracked: move quantities
                qty_delivered_change = sol.qty_delivered - old_vals[sol.id][0]
                qty_returned_change = sol.qty_returned - old_vals[sol.id][1]
                if qty_delivered_change > 0:
                    sol._move_qty(qty_delivered_change, stock_location, rented_location)
                elif qty_delivered_change < 0:
                    sol._return_qty(-qty_delivered_change, stock_location, rented_location)

                if qty_returned_change > 0.0:
                    sol._move_qty(qty_returned_change, rented_location, stock_location)
                elif qty_returned_change < 0.0:
                    sol._return_qty(-qty_returned_change, rented_location, stock_location)

    def _move_serials(self, lot_ids, location_id, location_dest_id):
        """Move the given lots from location_id to location_dest_id.

        :param stock.lot lot_ids:
        :param stock.location location_id:
        :param stock.location location_dest_id:
        """
        if not lot_ids:
            return
        rental_stock_move = self.env['stock.move'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': len(lot_ids),
            'product_uom': self.product_id.uom_id.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'partner_id': self.order_partner_id.id,
            'sale_line_id': self.id,
            'name': _("Rental move: %(order)s", order=self.order_id.name),
        })

        for lot_id in lot_ids:
            lot_quant = self.env['stock.quant']._gather(self.product_id, location_id, lot_id)
            lot_quant = lot_quant.filtered(lambda quant: quant.quantity == 1.0)
            if not lot_quant:
                raise ValidationError(_("No valid quant has been found in location %(location)s for serial number %(serial_number)s!", location=location_id.name, serial_number=lot_id.name))
                # Best fallback strategy??
                # Make a stock move without specifying quants and lots?
                # Let the move be created with the erroneous quant???
            # As we are using serial numbers, only one quant is expected
            ml = self.env['stock.move.line'].create(rental_stock_move._prepare_move_line_vals(reserved_quant=lot_quant))
            ml['quantity'] = 1

        rental_stock_move.picked = True
        rental_stock_move._action_done()

    def _return_serials(self, lot_ids, location_id, location_dest_id):
        """Undo the move of lot_ids from location_id to location_dest_id.

        :param stock.lot lot_ids:
        :param stock.location location_id:
        :param stock.location location_dest_id:
        """
        # VFE NOTE: or use stock moves to undo return/pickups???
        if not lot_ids:
            return
        rental_stock_move = self.env['stock.move'].search([
            ('sale_line_id', '=', self.id),
            ('location_id', '=', location_id.id),
            ('location_dest_id', '=', location_dest_id.id)
        ])
        for ml in rental_stock_move.mapped('move_line_ids'):
            # update move lines qties.
            if ml.lot_id.id in lot_ids:
                ml.quantity = 0.0

        rental_stock_move.product_uom_qty -= len(lot_ids)

    def _move_qty(self, qty, location_id, location_dest_id):
        """Move qty from location_id to location_dest_id.

        :param float qty:
        :param stock.location location_id:
        :param stock.location location_dest_id:
        """
        rental_stock_move = self.env['stock.move'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'partner_id': self.order_partner_id.id,
            'sale_line_id': self.id,
            'name': _("Rental move: %(order)s", order=self.order_id.name),
            'state': 'confirmed',
        })
        rental_stock_moves = rental_stock_move._set_rental_sm_qty()
        for move in rental_stock_moves:
            move._action_assign()
            move.quantity = move.product_uom_qty
            move.picked = True
        rental_stock_moves._action_done()

    def _return_qty(self, qty, location_id, location_dest_id):
        """Undo a qty move (partially or totally depending on qty).

        :param float qty:
        :param stock.location location_id:
        :param stock.location location_dest_id:
        """
        # VFE NOTE: or use stock moves to undo return/pickups???
        rental_stock_move = self.env['stock.move'].search([
            ('sale_line_id', '=', self.id),
            ('location_id', '=', location_id.id),
            ('location_dest_id', '=', location_dest_id.id)
        ], order='date desc')

        for ml in rental_stock_move.mapped('move_line_ids'):
            # update move lines qties.
            qty -= ml.quantity
            ml.quantity = 0.0 if qty > 0.0 else -qty

            if qty <= 0.0:
                return True
                # TODO ? ml.move_id.product_uom_qty -= decrease of qty

        return qty <= 0.0

    @api.constrains('product_id')
    def _stock_consistency(self):
        for line in self.filtered('is_rental'):
            moves = line.move_ids.filtered(lambda m: m.state != 'cancel')
            if moves and moves.mapped('product_id') != line.product_id:
                raise ValidationError(_("You cannot change the product of lines linked to stock moves."))

    def _create_procurements(self, product_qty, procurement_uom, origin, values):
        """ Change the destination for rental procurement groups. """
        if self.is_rental and self._are_rental_pickings_enabled():
            values['route_ids'] = values.get('route_ids') or self.env.ref('sale_stock_renting.route_rental')
            delivery_values = {
                **values,
                'date_planned': self.order_id.rental_start_date,
                'date_deadline': self.order_id.rental_start_date,
            }
            return_values = {
                **values,
                'date_planned': self.order_id.rental_return_date,
                'date_deadline': self.order_id.rental_return_date,
            }
            return [
                self.env['procurement.group'].Procurement(
                    self.product_id, product_qty, procurement_uom, self.order_id.company_id.rental_loc_id,
                    self.product_id.display_name, origin, self.order_id.company_id, delivery_values),
                self.env['procurement.group'].Procurement(
                    self.product_id, product_qty, procurement_uom, self.order_id.warehouse_id.lot_stock_id,
                    self.product_id.display_name, origin, self.order_id.company_id, return_values)]
        return super()._create_procurements(product_qty, procurement_uom, origin, values)

    def _action_launch_stock_rule(self, **kwargs):
        """ If the rental picking setting is deactivated:
        Disable stock moves for rental order lines.
        Stock moves for rental orders are created on pickup/return.
        The rental reservations are not propagated in the stock
        until the effective pickup or returns.

        If the rental picking setting is activated:
        Process all lines at the same time. """
        if not self or self._are_rental_pickings_enabled():
            super()._action_launch_stock_rule(**kwargs)
            returns = self.move_ids.filtered(lambda m: m.location_id == self.company_id.rental_loc_id)
            picks = self.move_ids.filtered(lambda m: m.location_id == self.warehouse_id.lot_stock_id)
            moves_by_order_line = defaultdict(lambda: {'picks': self.env['stock.move'], 'returns': self.env['stock.move']})
            for move in picks:
                if move.state in ('done', 'cancel'):
                    continue
                moves_by_order_line[move.sale_line_id]['picks'] |= move
            for move in returns:
                if move.state in ('done', 'cancel'):
                    continue
                moves_by_order_line[move.sale_line_id]['returns'] |= move
            returns._do_unreserve()
            for moves in moves_by_order_line.values():
                moves['returns'].write({
                    'move_orig_ids': [Command.link(pick.id) for pick in moves['picks']],
                    'procure_method': 'make_to_order'
                })
                moves['returns'].picking_id.return_id = moves['picks'].picking_id[:1]
            returns._recompute_state()
        else:
            other_lines = self.filtered(lambda sol: not sol.is_rental)
            super(RentalOrderLine, other_lines)._action_launch_stock_rule(**kwargs)

    def _get_outgoing_incoming_moves(self, strict=True):
        outgoing_moves, incoming_moves = super()._get_outgoing_incoming_moves(strict)
        if self.is_rental and self._are_rental_pickings_enabled():
            for move in self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id):
                if (
                        strict and move.location_dest_id == self.company_id.rental_loc_id or
                        not strict and move.location_id._child_of(self.order_id.warehouse_id.lot_stock_id)
                ):
                    outgoing_moves |= move
                elif strict and move.location_id == self.company_id.rental_loc_id:
                    incoming_moves |= move

        return outgoing_moves, incoming_moves

    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()

        if not self._are_rental_pickings_enabled():
            return

        for line in self:
            if line.is_rental:
                qty = 0.0
                outgoing_moves, dummy = line._get_outgoing_incoming_moves()
                for move in outgoing_moves:
                    if move.state != 'done':
                        continue
                    qty += move.product_uom._compute_quantity(move.quantity, line.product_uom, rounding_method='HALF-UP')
                line.qty_delivered = qty

    @api.depends('pickedup_lot_ids', 'returned_lot_ids', 'reserved_lot_ids')
    def _compute_unavailable_lots(self):
        """Unavailable lots = reserved_lots U pickedup_lots - returned_lots."""
        for line in self:
            line.unavailable_lot_ids = (line.reserved_lot_ids | line.pickedup_lot_ids) - line.returned_lot_ids

    @api.depends('start_date', 'is_rental')
    def _compute_reservation_begin(self):
        lines = self.filtered(lambda line: line.is_rental)
        for line in lines:
            padding_timedelta_before = timedelta(hours=line.product_id.preparation_time)
            line.reservation_begin = line.start_date and line.start_date - padding_timedelta_before
        (self - lines).reservation_begin = None

    def _get_rented_quantities(self, mandatory_dates):
        """ Return the quantities that are picked up (positive value) or returned (negative value),
        keyed by their pickup/return dates.

        This method also returns a sorted list of dates of interest, which is the union of the
        pickup/return dates and mandatory_dates.

        :param list(datetime) mandatory_dates: typically a "from" and a "to" date defining an
            interval of interest to the caller.
        """
        if not self:
            return defaultdict(float), sorted(set(mandatory_dates))
        self.product_id.ensure_one()
        rented_quantities = defaultdict(float)
        now = fields.Datetime.now()
        for so_line in self.filtered('is_rental'):
            rented_quantities[so_line.reservation_begin] += so_line.product_uom_qty
            rented_quantities[so_line.return_date] -= so_line.product_uom_qty
            # Adjust the rented quantities for early pickups.
            # We don't know when the order was picked up, so we apply the adjustment from the
            # current date to the expected pickup date.
            if so_line.reservation_begin > now and so_line.qty_delivered > 0:
                rented_quantities[now] += so_line.qty_delivered
                rented_quantities[so_line.reservation_begin] -= so_line.qty_delivered
            # Adjust the rented quantities for early returns.
            # We don't know when the order was returned, so we apply the adjustment from the current
            # date to the expected return date.
            if so_line.return_date > now and so_line.qty_returned > 0:
                rented_quantities[now] -= so_line.qty_returned
                rented_quantities[so_line.return_date] += so_line.qty_returned

        key_dates = sorted(set(rented_quantities.keys()) | set(mandatory_dates))
        return rented_quantities, key_dates

    def _are_rental_pickings_enabled(self):
        if self and self[0].order_id.create_uid:
            return self[0].order_id.create_uid.has_group(
                'sale_stock_renting.group_rental_stock_picking'
            )
        return self.env.user.has_group('sale_stock_renting.group_rental_stock_picking')
