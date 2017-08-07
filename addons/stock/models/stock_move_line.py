# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools.pycompat import izip
from odoo.tools.float_utils import float_round, float_compare, float_is_zero


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _description = "Packing Operation"
    _order = "result_package_id desc, id"


    picking_id = fields.Many2one(
        'stock.picking', 'Stock Picking',
        help='The stock operation where the packing has been made')
    move_id = fields.Many2one(
        'stock.move', 'Stock Move', 
        help="Change to a better name") 
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade") #might be a related with the move also --> no, because you can put them next to each other
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure', required=True)
    product_qty = fields.Float(
        'Real Reserved Quantity', digits=0,
        compute='_compute_product_qty', inverse='_set_product_qty', store=True)
    product_uom_qty = fields.Float('Reserved', default=0.0, digits=dp.get_precision('Product Unit of Measure'), required=True)
    ordered_qty = fields.Float('Ordered Quantity', digits=dp.get_precision('Product Unit of Measure'))
    qty_done = fields.Float('Done', default=0.0, digits=dp.get_precision('Product Unit of Measure'), copy=False)
    package_id = fields.Many2one('stock.quant.package', 'Source Package', ondelete='restrict')
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    lot_name = fields.Char('Lot/Serial Number')
    result_package_id = fields.Many2one(
        'stock.quant.package', 'Destination Package',
        ondelete='restrict', required=False,
        help="If set, the operations are packed into this package")
    date = fields.Datetime('Date', default=fields.Datetime.now(), required=True)
    owner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the quants")
    location_id = fields.Many2one('stock.location', 'From', required=True)
    location_dest_id = fields.Many2one('stock.location', 'To', required=True)
    from_loc = fields.Char(compute='_compute_location_description')
    to_loc = fields.Char(compute='_compute_location_description')
    lots_visible = fields.Boolean(compute='_compute_lots_visible')
    state = fields.Selection(related='move_id.state')
    consume_line_ids = fields.Many2many('stock.move.line', 'stock_move_line_consume_rel', 'consume_line_id', 'produce_line_id', help="Technical link to see who consumed what. ")
    produce_line_ids = fields.Many2many('stock.move.line', 'stock_move_line_consume_rel', 'produce_line_id', 'consume_line_id', help="Technical link to see which line was produced with this. ")


    @api.one
    def _compute_location_description(self):
        for operation, operation_sudo in izip(self, self.sudo()):
            operation.from_loc = '%s%s' % (operation_sudo.location_id.name, operation.product_id and operation_sudo.package_id.name or '')
            operation.to_loc = '%s%s' % (operation_sudo.location_dest_id.name, operation_sudo.result_package_id.name or '')

    @api.one
    @api.depends('picking_id.picking_type_id', 'product_id.tracking')
    def _compute_lots_visible(self):
        picking = self.picking_id
        if picking.picking_type_id and self.product_id.tracking != 'none':  # TDE FIXME: not sure correctly migrated
            self.lots_visible = picking.picking_type_id.use_existing_lots or picking.picking_type_id.use_create_lots
        else:
            self.lots_visible = self.product_id.tracking != 'none'

    @api.one
    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_product_qty(self):
        self.product_qty = self.product_uom_id._compute_quantity(self.product_uom_qty, self.product_id.uom_id, rounding_method='HALF-UP')

    @api.one
    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

    @api.multi
    @api.onchange('product_id', 'product_uom_id')
    def onchange_product_id(self):
        if self.product_id:
            self.lots_visible = self.product_id.tracking != 'none'
            if not self.product_uom_id or self.product_uom_id.category_id != self.product_id.uom_id.category_id:
                if self.move_id.product_uom:
                    self.product_uom_id = self.move_id.product_uom.id
                else:
                    self.product_uom_id = self.product_id.uom_id.id
            res = {'domain': {'product_uom_id': [('category_id', '=', self.product_uom_id.category_id.id)]}}
        else:
            res = {'domain': {'product_uom_id': []}}
        return res

    @api.model
    def create(self, vals):
        vals['ordered_qty'] = vals.get('product_uom_qty')
        ml = super(StockMoveLine, self).create(vals)
        if ml.state == 'done':
            Quant = self.env['stock.quant']
            quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id,rounding_method='HALF-UP')
            in_date = None
            if ml.location_id.should_impact_quants() and ml.product_id.type == 'product':
                available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                if available_qty < 0 and ml.lot_id:
                    # see if we can compensate the negative quants with some untracked quants
                    untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                    if untracked_qty:
                        taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                        Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id)
                        Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
            if ml.location_dest_id.should_impact_quants() and ml.product_id.type == 'product':
                Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date)
            next_moves = ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))
            next_moves.do_unreserve()
            next_moves.action_assign()
        return ml

    @api.multi
    def write(self, vals):
        """ Through the interface, we allow users to change the charateristics of a move line. If a
        quantity has been reserved for this move line, we impact the reservation directly to free
        the old quants and allocate the new ones.
        """
        if self.env.context.get('bypass_reservation_update'):
            return super(StockMoveLine, self).write(vals)

        Quant = self.env['stock.quant']
        # We forbid to change the reserved quantity in the interace, but it is needed in the
        # case of stock.move's split.
        # TODO Move me in the update
        if 'product_uom_qty' in vals:
            for ml in self.filtered(lambda m: m.state in ('partially_available', 'assigned')):
                if ml.location_id.should_impact_quants() and ml.product_id.type == 'product':
                    qty_to_decrease = ml.product_qty - ml.product_uom_id._compute_quantity(vals['product_uom_qty'], ml.product_id.uom_id, rounding_method='HALF-UP')
                    try:
                        Quant._update_reserved_quantity(ml.product_id, ml.location_id, -qty_to_decrease, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                    except UserError:
                        if ml.lot_id:
                            Quant._update_reserved_quantity(ml.product_id, ml.location_id, -qty_to_decrease, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                        else:
                            raise

        triggers = [
            ('location_id', 'stock.location'),
            ('location_dest_id', 'stock.location'),
            ('lot_id', 'stock.production.lot'),
            ('package_id', 'stock.quant.package'),
            ('result_package_id', 'stock.quant.package'),
            ('owner_id', 'res.partner')
        ]
        updates = {}
        for key, model in triggers:
            if key in vals:
                updates[key] = self.env[model].browse(vals[key])

        if updates:
            for ml in self.filtered(lambda ml: ml.state in ['partially_available', 'assigned']):
                if ml.location_id.should_impact_quants() and ml.product_id.type == 'product':
                    try:
                        Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                    except UserError:
                        if ml.lot_id:
                            Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                        else:
                            raise

                if updates.get('location_id', ml.location_id).should_impact_quants() and ml.product_id.type == 'product':
                    new_product_qty = 0
                    try:
                        q = Quant._update_reserved_quantity(ml.product_id, updates.get('location_id', ml.location_id), ml.product_qty, lot_id=updates.get('lot_id', ml.lot_id),
                                                             package_id=updates.get('package_id', ml.package_id), owner_id=updates.get('owner_id', ml.owner_id), strict=True)
                        new_product_qty = sum([x[1] for x in q])
                    except UserError:
                        if updates.get('lot_id'):
                            # If we were not able to reserve on tracked quants, we can use untracked ones.
                            try:
                                q = Quant._update_reserved_quantity(ml.product_id, updates.get('location_id', ml.location_id), ml.product_qty, lot_id=False,
                                                                     package_id=updates.get('package_id', ml.package_id), owner_id=updates.get('owner_id', ml.owner_id), strict=True)
                                new_product_qty = sum([x[1] for x in q])
                            except UserError:
                                pass
                    if new_product_qty != ml.product_qty:
                        new_product_uom_qty = self.product_id.uom_id._compute_quantity(new_product_qty, self.product_uom_id, rounding_method='HALF-UP')
                        ml.with_context(bypass_reservation_update=True).product_uom_qty = new_product_uom_qty

        # When editing a done move line, the reserved availability of a potential chained move is impacted. Take care of running again `action_assign` on the concerned moves.
        next_moves = self.env['stock.move']
        if updates or 'qty_done' in vals:
            for ml in self.filtered(lambda ml: ml.move_id.state == 'done'):
                # undo the original move line
                in_date = None
                if ml.location_dest_id.should_impact_quants() and ml.product_id.type == 'product':
                    in_date = Quant._update_available_quantity(ml.product_id, ml.location_dest_id, -ml.qty_done, lot_id=ml.lot_id,
                                                      package_id=ml.package_id, owner_id=ml.owner_id)[1]
                if ml.location_id.should_impact_quants() and ml.product_id.type == 'product':
                    Quant._update_available_quantity(ml.product_id, ml.location_id, ml.qty_done, lot_id=ml.lot_id,
                                                      package_id=ml.package_id, owner_id=ml.owner_id, in_date=in_date)

                # move what's been actually done
                in_date = None
                product_id = ml.product_id
                location_id = updates.get('location_id', ml.location_id)
                location_dest_id = updates.get('location_dest_id', ml.location_dest_id)
                qty_done = vals.get('qty_done', ml.qty_done)
                lot_id = updates.get('lot_id', ml.lot_id)
                package_id = updates.get('package_id', ml.package_id)
                result_package_id = updates.get('result_package_id', ml.result_package_id)
                owner_id = updates.get('owner_id', ml.owner_id)
                quantity = ml.move_id.product_uom._compute_quantity(qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
                if location_id.should_impact_quants() and ml.product_id.type == 'product':
                    ml._free_reservation(product_id, location_id, quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
                    available_qty, in_date = Quant._update_available_quantity(product_id, location_id, -quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
                    if available_qty < 0 and lot_id:
                        # see if we can compensate the negative quants with some untracked quants
                        untracked_qty = Quant._get_available_quantity(product_id, location_id, lot_id=False, package_id=package_id, owner_id=owner_id, strict=True)
                        if untracked_qty:
                            taken_from_untracked_qty = min(untracked_qty, abs(available_qty))
                            Quant._update_available_quantity(product_id, location_id, -taken_from_untracked_qty, lot_id=False, package_id=package_id, owner_id=owner_id)
                            Quant._update_available_quantity(product_id, location_id, taken_from_untracked_qty, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
                            ml._free_reservation(ml.product_id, location_id, untracked_qty, lot_id=False, package_id=package_id, owner_id=owner_id)
                if location_dest_id.should_impact_quants() and ml.product_id.type == 'product' and qty_done:
                    Quant._update_available_quantity(product_id, location_dest_id, quantity, lot_id=lot_id, package_id=result_package_id, owner_id=owner_id, in_date=in_date)
                # Unreserve and reserve following move in order to have the real reserved quantity on move_line.
                next_moves |= ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))
        res = super(StockMoveLine, self).write(vals)
        next_moves.do_unreserve()
        next_moves.action_assign()
        return res

    @api.multi
    def unlink(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for ml in self:
            if ml.state in ('done', 'cancel'):
                raise UserError(_('You can not delete pack operations of a done picking'))
            # Unlinking a pack operation should unreserve.
            if ml.location_id.should_impact_quants() and ml.product_id.type == 'product' and not float_is_zero(ml.product_qty, precision_digits=precision):
                self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id,
                                                                   package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
        return super(StockMoveLine, self).unlink()

    def action_done(self):
        """ This method is called during a move's `action_done`. It'll actually move a quant from
        the source location to the destination location, and unreserve if needed in the source
        location.

        This method is intended to be called on all the move lines of a move. This method is not
        intended to be called when editing a `done` move (that's what the override of `write` here
        is done.
        """

        # First, we loop over all the move lines to do a preliminary check: `qty_done` should not
        # be negative and, according to the presence of a picking type or a linked inventory
        # adjustment, enforce some rules on the `lot_id` field. If `qty_done` is null, we unlink
        # the line. It is mandatory in order to free the reservation and correctly apply
        # `action_done` on the next move lines.
        ml_to_delete = self.env['stock.move.line']
        for ml in self:
            qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking != 'none':
                    picking_type_id = ml.move_id.picking_type_id
                    if picking_type_id:
                        if picking_type_id.use_create_lots:
                            # If a picking type is linked, we may have to create a production lot on
                            # the fly before assigning it to the move line if the user checked both
                            # `use_create_lots` and `use_existing_lots`.
                            if ml.lot_name and not ml.lot_id:
                                lot = self.env['stock.production.lot'].create(
                                    {'name': ml.lot_name, 'product_id': ml.product_id.id}
                                )
                                ml.write({'lot_id': lot.id})
                        elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
                            # If the user disabled both `use_create_lots` and `use_existing_lots`
                            # checkboxes on the picking type, he's allowed to enter tracked
                            # products without a `lot_id`.
                            continue
                    elif ml.move_id.inventory_id:
                        # If an inventory adjustment is linked, the user is allowed to enter
                        # tracked products without a `lot_id`.
                        continue

                    if not ml.lot_id:
                        raise UserError(_('You need to supply a lot/serial number.'))
            elif qty_done_float_compared < 0:
                raise UserError(_('No negative quantities allowed'))
            else:
                ml_to_delete |= ml
        ml_to_delete.unlink()

        # Now, we can actually move the quant.
        for ml in self - ml_to_delete:
            if ml.product_id.type != 'consu':
                Quant = self.env['stock.quant']
                rounding = ml.product_uom_id.rounding

                # if this move line is force assigned, unreserve elsewhere if needed
                if ml.location_id.should_impact_quants() and float_compare(ml.qty_done, ml.product_qty, precision_rounding=rounding) > 0:
                    extra_qty = ml.qty_done - ml.product_qty
                    ml._free_reservation(ml.product_id, ml.location_id, extra_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                # unreserve what's been reserved
                if ml.location_id.should_impact_quants() and ml.product_id.type == 'product' and ml.product_qty:
                    try:
                        Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                    except UserError:
                        Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

                # move what's been actually done
                quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
                in_date = None
                if ml.location_id.should_impact_quants() and ml.product_id.type == 'product':
                    available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                    if available_qty < 0 and ml.lot_id:
                        # see if we can compensate the negative quants with some untracked quants
                        untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                        if untracked_qty:
                            taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                            Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id)
                            Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                if ml.location_dest_id.should_impact_quants() and ml.product_id.type == 'product':
                    Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date)

    def _free_reservation(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None):
        """ When editing a done move line or validating one with some forced quantities, it is
        possible to impact quants that were not reserved. It is therefore necessary to edit or
        unlink the move lines that reserved a quantity now unavailable.
        """
        self.ensure_one()

        # Check the available quantity, with the `strict` kw set to `True`. If the available
        # quantity is greather than the quantity now unavailable, there is nothing to do.
        available_quantity = self.env['stock.quant']._get_available_quantity(
            product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True
        )
        if quantity > available_quantity:
            # We now have to find the move lines that reserved our now unavailable quantity. We
            # take care to exclude ourselves and the move lines were work had already been done.
            oudated_move_lines_domain = [
                ('move_id.state', 'not in', ['done', 'cancel']),
                ('product_id', '=', product_id.id),
                ('lot_id', '=', lot_id.id if lot_id else False),
                ('location_id', '=', location_id.id),
                ('owner_id', '=', owner_id.id if owner_id else False),
                ('package_id', '=', package_id.id if package_id else False),
                ('product_qty', '>', 0.0),
                ('qty_done', '=', 0.0),
                ('id', '!=', self.id),
            ]
            oudated_candidates = self.env['stock.move.line'].search(oudated_move_lines_domain)

            # As the move's state is not computed over the move lines, we'll have to manually
            # recompute the moves which we adapted their lines.
            move_to_recompute_state = self.env['stock.move']

            rounding = self.product_uom_id.rounding
            for candidate in oudated_candidates:
                if float_compare(candidate.product_qty, quantity, precision_rounding=rounding) <= 0:
                    quantity -= candidate.product_qty
                    move_to_recompute_state |= candidate.move_id
                    candidate.unlink()
                else:
                    # split this move line and assign the new part to our extra move
                    quantity_split = float_round(
                        candidate.product_qty - quantity,
                        precision_rounding=self.product_uom_id.rounding,
                        rounding_method='UP')
                    candidate.product_uom_qty = self.product_id.uom_id._compute_quantity(quantity_split, self.product_uom_id, rounding_method='HALF-UP')
                    quantity -= quantity_split
                    move_to_recompute_state |= candidate.move_id
                if quantity == 0.0:
                    break
            move_to_recompute_state._recompute_state()
