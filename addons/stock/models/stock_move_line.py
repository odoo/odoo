# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter, defaultdict
from ast import literal_eval

from odoo import _, api, fields, models
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import OrderedSet, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockMoveLine(models.Model):
    _name = 'stock.move.line'
    _description = "Product Moves (Stock Move Line)"
    _rec_name = "product_id"
    _order = "result_package_id desc, id"

    picking_id = fields.Many2one(
        'stock.picking', 'Transfer', bypass_search_access=True,
        check_company=True,
        index=True,
        help='The stock operation where the packing has been made')
    move_id = fields.Many2one(
        'stock.move', 'Stock Operation',
        check_company=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True, index=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade", check_company=True, domain="[('type', '!=', 'service')]", index=True)
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit', required=True, domain="[('id', 'in', allowed_uom_ids)]",
        compute="_compute_product_uom_id", store=True, readonly=False, precompute=True,
    )
    product_category_name = fields.Char(related="product_id.categ_id.complete_name", string="Product Category")
    quantity = fields.Float(
        'Quantity', digits='Product Unit', copy=False, store=True,
        compute='_compute_quantity', readonly=False)
    quantity_product_uom = fields.Float(
        'Quantity in Product UoM', digits='Product Unit',
        copy=False, compute='_compute_quantity_product_uom', store=True)
    picked = fields.Boolean('Picked', compute='_compute_picked', store=True, readonly=False, copy=False)
    package_id = fields.Many2one(
        'stock.package', 'Source Package', ondelete='restrict',
        check_company=True,
        domain="[('location_id', '=', location_id)]")
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id)]", check_company=True)
    lot_name = fields.Char('Lot/Serial Number Name')
    result_package_id = fields.Many2one(
        'stock.package', 'Destination Package',
        ondelete='restrict', required=False, check_company=True,
        domain="['|', '|', ('location_id', '=', False), ('location_id', '=', location_dest_id), ('id', '=', package_id)]",
        help="If set, the operations are packed into this package")
    result_package_dest_name = fields.Char('Destination Package Name', related='result_package_id.dest_complete_name')
    package_history_id = fields.Many2one('stock.package.history', string="Package History", index='btree_not_null')
    is_entire_pack = fields.Boolean('Is added through entire package')
    date = fields.Datetime(
        'Date', default=fields.Datetime.now, required=True,
        help="Creation date of this move line until updated due to: quantity being increased, 'picked' status has updated, or move line is done.")
    scheduled_date = fields.Datetime('Scheduled Date', related='move_id.date')
    owner_id = fields.Many2one(
        'res.partner', 'From Owner',
        check_company=True, index='btree_not_null',
        help="When validating the transfer, the products will be taken from this owner.")
    location_id = fields.Many2one(
        'stock.location', 'From', domain="[('usage', '!=', 'view')]", check_company=True, required=True,
        compute="_compute_location_id", store=True, readonly=False, precompute=True, index=True,
    )
    location_dest_id = fields.Many2one('stock.location', 'To', domain="[('usage', '!=', 'view')]", check_company=True, required=True, compute="_compute_location_id", store=True, index=True, readonly=False, precompute=True)
    location_usage = fields.Selection(string="Source Location Type", related='location_id.usage')
    location_dest_usage = fields.Selection(string="Destination Location Type", related='location_dest_id.usage')
    lots_visible = fields.Boolean(compute='_compute_lots_visible')
    picking_partner_id = fields.Many2one(related='picking_id.partner_id', readonly=True)
    move_partner_id = fields.Many2one(related='move_id.partner_id', readonly=True)
    picking_code = fields.Selection(related='picking_type_id.code', readonly=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation type', compute='_compute_picking_type_id', search='_search_picking_type_id')
    picking_type_use_create_lots = fields.Boolean(related='picking_type_id.use_create_lots', readonly=True)
    picking_type_use_existing_lots = fields.Boolean(related='picking_type_id.use_existing_lots', readonly=True)
    state = fields.Selection(related='move_id.state', store=True)
    scrap_id = fields.Many2one(related='move_id.scrap_id')
    is_inventory = fields.Boolean(related='move_id.is_inventory')
    is_locked = fields.Boolean(related='move_id.is_locked', readonly=True)
    consume_line_ids = fields.Many2many('stock.move.line', 'stock_move_line_consume_rel', 'consume_line_id', 'produce_line_id')
    produce_line_ids = fields.Many2many('stock.move.line', 'stock_move_line_consume_rel', 'produce_line_id', 'consume_line_id')
    reference = fields.Char(related='move_id.reference', readonly=False)
    tracking = fields.Selection(related='product_id.tracking', readonly=True)
    origin = fields.Char(related='move_id.origin', string='Source')
    description_picking = fields.Text(related='move_id.description_picking')
    quant_id = fields.Many2one('stock.quant', "Pick From", store=False)  # Dummy field for the detailed operation view
    picking_location_id = fields.Many2one(related='picking_id.location_id')
    picking_location_dest_id = fields.Many2one(related='picking_id.location_dest_id')

    _free_reservation_index = models.Index("""(id, company_id, product_id, lot_id, location_id, owner_id, package_id)
        WHERE (state IS NULL OR state NOT IN ('cancel', 'done')) AND quantity_product_uom > 0 AND picked IS NOT TRUE""")

    @api.depends('product_id', 'product_id.uom_id', 'product_id.uom_ids', 'product_id.seller_ids', 'product_id.seller_ids.product_uom_id')
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id.uom_id | line.product_id.uom_ids | line.sudo().product_id.seller_ids.product_uom_id

    @api.depends('move_id.product_uom', 'product_id.uom_id')
    def _compute_product_uom_id(self):
        for line in self:
            if not line.product_uom_id:
                if line.move_id.product_uom:
                    line.product_uom_id = line.move_id.product_uom.id
                else:
                    line.product_uom_id = line.product_id.uom_id.id

    @api.depends('picking_id.picking_type_id', 'product_id.tracking')
    def _compute_lots_visible(self):
        for line in self:
            picking = line.picking_id
            if picking.picking_type_id and line.product_id.tracking != 'none':  # TDE FIXME: not sure correctly migrated
                line.lots_visible = picking.picking_type_id.use_existing_lots or picking.picking_type_id.use_create_lots
            else:
                line.lots_visible = line.product_id.tracking != 'none'

    @api.depends('state')
    def _compute_picked(self):
        for line in self:
            if line.move_id.state == 'done':
                line.picked = True

    @api.depends('picking_id')
    def _compute_picking_type_id(self):
        self.picking_type_id = False
        for line in self:
            if line.picking_id:
                line.picking_type_id = line.picking_id.picking_type_id

    @api.depends('move_id', 'move_id.location_id', 'move_id.location_dest_id', 'picking_id')
    def _compute_location_id(self):
        for line in self:
            if not line.location_id or line._origin.picking_id.location_id != line.picking_id.location_id:
                line.location_id = line.move_id.location_id or line.picking_id.location_id
            if not line.location_dest_id or line._origin.picking_id.location_dest_id != line.picking_id.location_dest_id:
                line.location_dest_id = line.move_id.location_dest_id or line.picking_id.location_dest_id

    def _search_picking_type_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return Domain('picking_id.picking_type_id', operator, value)

    @api.depends('quant_id')
    def _compute_quantity(self):
        for record in self:
            if not record.quant_id or record.quantity:
                continue
            product_uom = record.product_id.uom_id
            sml_uom = record.product_uom_id
            move_visible_quantity = record.move_id and record.move_id._visible_quantity() or 0.0

            move_demand = record.move_id.product_uom._compute_quantity(record.move_id.product_uom_qty, sml_uom, rounding_method='HALF-UP')
            move_quantity = record.move_id.product_uom._compute_quantity(move_visible_quantity, sml_uom, rounding_method='HALF-UP')
            quant_qty = product_uom._compute_quantity(record.quant_id.available_quantity, sml_uom, rounding_method='HALF-UP')

            if sml_uom.compare(move_demand, move_quantity) > 0:
                record.quantity = max(0, min(quant_qty, move_demand - move_quantity))
            else:
                record.quantity = max(0, quant_qty)

    @api.depends('quantity', 'product_uom_id')
    def _compute_quantity_product_uom(self):
        for line in self:
            line.quantity_product_uom = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id, rounding_method='HALF-UP')

    @api.constrains('lot_id', 'product_id')
    def _check_lot_product(self):
        for line in self:
            if line.lot_id and line.product_id != line.lot_id.sudo().product_id:
                raise ValidationError(_(
                    'This lot %(lot_name)s is incompatible with this product %(product_name)s',
                    lot_name=line.lot_id.name,
                    product_name=line.product_id.display_name
                ))

    @api.constrains('quantity')
    def _check_positive_quantity(self):
        if any(ml.quantity < 0 for ml in self):
            raise ValidationError(_('You can not enter negative quantities.'))

    @api.onchange('product_id', 'product_uom_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.lots_visible = self.product_id.tracking != 'none'

    @api.onchange('lot_name', 'lot_id')
    def _onchange_serial_number(self):
        """ When the user is encoding a move line for a tracked product, we apply some logic to
        help him. This includes:
            - automatically switch `quantity` to 1.0
            - warn if he has already encoded `lot_name` in another move line
            - warn (and update if appropriate) if the SN is in a different source location than selected
        """
        res = {}
        if self.product_id.tracking == 'serial':
            if not self.quantity:
                self.quantity = 1

            message = None
            if self.lot_name or self.lot_id:
                move_lines_to_check = self._get_similar_move_lines() - self
                if self.lot_name:
                    counter = Counter([line.lot_name for line in move_lines_to_check])
                    if counter.get(self.lot_name) and counter[self.lot_name] > 1:
                        message = _('You cannot use the same serial number twice. Please correct the serial numbers encoded.')
                    elif not self.lot_id:
                        lots = self.env['stock.lot'].search([('product_id', '=', self.product_id.id),
                                                             ('name', '=', self.lot_name),
                                                             '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])
                        quants = lots.quant_ids.filtered(lambda q: q.quantity != 0 and q.location_id.usage in ['customer', 'internal', 'transit'])
                        if quants:
                            message = _(
                                'Serial number (%(serial_number)s) already exists in location(s): %(location_list)s. Please correct the serial number encoded.',
                                serial_number=self.lot_name,
                                location_list=quants.location_id.mapped('display_name')
                            )
                elif self.lot_id:
                    counter = Counter([line.lot_id.id for line in move_lines_to_check])
                    if counter.get(self.lot_id.id) and counter[self.lot_id.id] > 1:
                        message = _('You cannot use the same serial number twice. Please correct the serial numbers encoded.')
                    else:
                        # check if in correct source location
                        message, recommended_location = self.env['stock.quant'].sudo()._check_serial_number(
                            self.product_id, self.lot_id, self.company_id, self.location_id, self.picking_id.location_id)
                        if recommended_location:
                            self.location_id = recommended_location
            if message:
                res['warning'] = {'title': _('Warning'), 'message': message}
        return res

    @api.onchange('quantity', 'product_uom_id')
    def _onchange_quantity(self):
        """ When the user is encoding a move line for a tracked product, we apply some logic to
        help him. This onchange will warn him if he set `quantity` to a non-supported value.
        """
        res = {}
        if self.quantity and self.product_id.tracking == 'serial':
            if self.product_id.uom_id.compare(self.quantity_product_uom, 1.0) != 0 and not self.product_id.uom_id.is_zero(self.quantity_product_uom):
                raise UserError(_('You can only process 1.0 %s of products with unique serial number.', self.product_id.uom_id.name))
        return res

    @api.onchange('result_package_id', 'product_id', 'product_uom_id', 'quantity')
    def _onchange_putaway_location(self):
        default_dest_location = self._get_default_dest_location()
        if not self.id and self.env.user.has_group('stock.group_stock_multi_locations') and self.product_id and self.quantity_product_uom \
                and self.location_dest_id == default_dest_location:
            quantity = self.quantity_product_uom
            self.location_dest_id = default_dest_location.with_context(exclude_sml_ids=self.ids)._get_putaway_strategy(
                self.product_id, quantity=quantity, package=self.result_package_id)

    def _apply_putaway_strategy(self):
        if self.env.context.get('avoid_putaway_rules'):
            return
        self = self.with_context(do_not_unreserve=True)
        for package, smls in groupby(self, lambda sml: sml.result_package_id):
            smls = self.env['stock.move.line'].concat(*smls)
            excluded_smls = set(smls.ids)
            if package.package_type_id:
                best_loc = smls.move_id.location_dest_id.with_context(exclude_sml_ids=excluded_smls, products=smls.product_id)._get_putaway_strategy(self.env['product.product'], package=package)
                smls.location_dest_id = best_loc
            elif package:
                used_locations = set()
                for sml in smls:
                    if len(used_locations) > 1:
                        break
                    sml.location_dest_id = sml.move_id.location_dest_id.with_context(exclude_sml_ids=excluded_smls)._get_putaway_strategy(sml.product_id, quantity=sml.quantity)
                    excluded_smls.discard(sml.id)
                    used_locations.add(sml.location_dest_id)
                if len(used_locations) > 1:
                    for move, grouped_smls in smls.grouped('move_id').items():
                        grouped_smls.location_dest_id = move.location_dest_id
            else:
                for sml in smls:
                    putaway_loc_id = sml.move_id.location_dest_id.with_context(exclude_sml_ids=excluded_smls)._get_putaway_strategy(
                        sml.product_id, quantity=sml.quantity, packaging=sml.move_id.packaging_uom_id,
                    )
                    if putaway_loc_id != sml.location_dest_id:
                        sml.location_dest_id = putaway_loc_id
                    excluded_smls.discard(sml.id)

    def _get_default_dest_location(self):
        if not self.env.user.has_group('stock.group_stock_multi_locations'):
            return self.location_dest_id[:1]
        if self.env.context.get('default_location_dest_id'):
            return self.env['stock.location'].browse([self.env.context.get('default_location_dest_id')])
        return (self.move_id.location_dest_id or self.picking_id.location_dest_id or self.location_dest_id)[:1]

    def _get_putaway_additional_qty(self):
        addtional_qty = {}
        for ml in self._origin:
            qty = ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id)
            addtional_qty[ml.location_dest_id.id] = addtional_qty.get(ml.location_dest_id.id, 0) - qty
        return addtional_qty

    def get_move_line_quant_match(self, move_id, dirty_move_line_ids, dirty_quant_ids):
        # Since the quant_id field is neither stored nor computed, this method is used to compute the match if it exists
        move = self.env['stock.move'].browse(move_id)
        deleted_move_lines = move.move_line_ids - self
        dirty_move_lines = self.env['stock.move.line'].browse(dirty_move_line_ids)
        quants_data = []
        move_lines_data = []
        domain = Domain("id", "in", dirty_quant_ids) | Domain.OR(
            Domain([
                ("product_id", "=", move_line.product_id.id),
                ("lot_id", "=", move_line.lot_id.id),
                ("location_id", "=", move_line.location_id.id),
                ("package_id", "=", move_line.package_id.id),
                ("owner_id", "=", move_line.owner_id.id),
            ])
            for move_line in dirty_move_lines | deleted_move_lines
        )
        if not domain.is_false():
            quants = self.env['stock.quant'].search(domain)
            for quant in quants:
                dirty_lines = dirty_move_lines.filtered(lambda ml: ml.product_id == quant.product_id
                    and ml.lot_id == quant.lot_id
                    and ml.location_id == quant.location_id
                    and ml.package_id == quant.package_id
                    and ml.owner_id == quant.owner_id
                )
                deleted_lines = deleted_move_lines.filtered(lambda ml: ml.product_id == quant.product_id
                    and ml.lot_id == quant.lot_id
                    and ml.location_id == quant.location_id
                    and ml.package_id == quant.package_id
                    and ml.owner_id == quant.owner_id
                )
                quants_data.append((quant.id, {"available_quantity": quant.available_quantity + sum(ml.quantity_product_uom for ml in deleted_lines), "move_line_ids": dirty_lines.ids}))
                move_lines_data += [(ml.id, {"quantity": ml.quantity, "quant_id": quant.id}) for ml in dirty_lines]
        return [quants_data, move_lines_data]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('move_id'):
                vals['company_id'] = self.env['stock.move'].browse(vals['move_id']).company_id.id
            elif vals.get('picking_id'):
                vals['company_id'] = self.env['stock.picking'].browse(vals['picking_id']).company_id.id
            if vals.get('move_id') and 'picked' not in vals:
                vals['picked'] = self.env['stock.move'].browse(vals['move_id']).picked
            if vals.get('quant_id'):
                vals.update(self._copy_quant_info(vals))

        mls = super().create(vals_list)

        created_moves = set()

        def create_move(move_line):
            new_move = self.env['stock.move'].create(move_line._prepare_stock_move_vals())
            move_line.move_id = new_move.id
            created_moves.add(new_move.id)

        # If the move line is directly create on the picking view.
        # If this picking is already done we should generate an
        # associated done move.
        for move_line in mls:
            if move_line.move_id or not move_line.picking_id:
                continue
            if move_line.picking_id.state != 'done':
                moves = move_line._get_linkable_moves()
                if moves:
                    vals = {
                        'move_id': moves[0].id,
                        'picking_id': moves[0].picking_id.id,
                    }
                    if moves[0].picked:
                        vals['picked'] = True
                    move_line.write(vals)
                else:
                    create_move(move_line)
            else:
                create_move(move_line)

        move_to_recompute_state = set()
        for move_line in mls:
            if move_line.state == 'done':
                continue
            location = move_line.location_id
            product = move_line.product_id
            move = move_line.move_id
            if move:
                reservation = not move._should_bypass_reservation()
            else:
                reservation = product.is_storable and not location.should_bypass_reservation()
            if move_line.quantity_product_uom and reservation:
                self.env.context.get('reserved_quant', self.env['stock.quant'])._update_reserved_quantity(
                    product, location, move_line.quantity_product_uom, lot_id=move_line.lot_id, package_id=move_line.package_id, owner_id=move_line.owner_id)

                if move:
                    move_to_recompute_state.add(move.id)
        self.env['stock.move'].browse(move_to_recompute_state)._recompute_state()
        self.env['stock.move'].browse(created_moves)._post_process_created_moves()

        for ml in mls:
            if ml.state == 'done':
                if ml.product_id.is_storable:
                    Quant = self.env['stock.quant']
                    quantity = ml.product_uom_id._compute_quantity(ml.quantity, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
                    available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                    if available_qty < 0 and ml.lot_id:
                        # see if we can compensate the negative quants with some untracked quants
                        untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                        if untracked_qty:
                            taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                            Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id)
                            Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                    Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date)
                next_moves = ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))
                next_moves._do_unreserve()
                next_moves._action_assign()
        move_done = mls.filtered(lambda m: m.state == "done").move_id
        if move_done:
            move_done._check_quantity()
        return mls

    def write(self, vals):
        if 'product_id' in vals and any(vals.get('state', ml.state) != 'draft' and vals['product_id'] != ml.product_id.id for ml in self):
            raise UserError(_("Changing the product is only allowed in 'Draft' state."))

        if ('lot_id' in vals or 'quant_id' in vals) and len(self.product_id) > 1:
            raise UserError(_("Changing the Lot/Serial number for move lines with different products is not allowed."))

        moves_to_recompute_state = self.env['stock.move']
        packages_to_check = self.env['stock.package']
        if 'result_package_id' in vals:
            # Either changed the result package or removed it
            packages_to_check = self.env['stock.package'].browse(self.result_package_id._get_all_package_dest_ids())
        triggers = [
            ('location_id', 'stock.location'),
            ('location_dest_id', 'stock.location'),
            ('lot_id', 'stock.lot'),
            ('package_id', 'stock.package'),
            ('result_package_id', 'stock.package'),
            ('owner_id', 'res.partner'),
            ('product_uom_id', 'uom.uom')
        ]
        if vals.get('quant_id'):
            vals.update(self._copy_quant_info(vals))
        updates = {}
        for key, model in triggers:
            if self.env.context.get('skip_uom_conversion'):
                continue
            if key in vals:
                updates[key] = vals[key] if isinstance(vals[key], models.BaseModel) else self.env[model].browse(vals[key])

        # When we try to write on a reserved move line any fields from `triggers`, result_package_id excepted,
        # or directly reserved_uom_qty` (the actual reserved quantity), we need to make sure the associated
        # quants are correctly updated in order to not make them out of sync (i.e. the sum of the
        # move lines `reserved_uom_qty` should always be equal to the sum of `reserved_quantity` on
        # the quants). If the new charateristics are not available on the quants, we chose to
        # reserve the maximum possible.
        if (updates and {'result_package_id'}.difference(updates.keys())) or 'quantity' in vals:
            for ml in self:
                if not ml.product_id.is_storable or ml.state == 'done':
                    continue
                if 'quantity' in vals or 'product_uom_id' in vals:
                    new_ml_uom = updates.get('product_uom_id', ml.product_uom_id)
                    new_reserved_qty = new_ml_uom._compute_quantity(
                        vals.get('quantity', ml.quantity), ml.product_id.uom_id, rounding_method='HALF-UP')
                    # Make sure `reserved_uom_qty` is not negative.
                    if ml.product_id.uom_id.compare(new_reserved_qty, 0) < 0:
                        raise UserError(_('Reserving a negative quantity is not allowed.'))
                else:
                    new_reserved_qty = ml.quantity_product_uom

                # Unreserve the old charateristics of the move line.
                if not ml.product_uom_id.is_zero(ml.quantity_product_uom):
                    ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, action="reserved")

                # Reserve the maximum available of the new charateristics of the move line.
                if not ml.move_id._should_bypass_reservation(updates.get('location_id', ml.location_id)):
                    ml._synchronize_quant(
                        new_reserved_qty, updates.get('location_id', ml.location_id), action="reserved",
                        lot=updates.get('lot_id', ml.lot_id), package=updates.get('package_id', ml.package_id),
                        owner=updates.get('owner_id', ml.owner_id))

                if ('quantity' in vals and vals['quantity'] != ml.quantity) or 'product_uom_id' in vals:
                    moves_to_recompute_state |= ml.move_id

        # When editing a done move line, the reserved availability of a potential chained move is impacted. Take care of running again `_action_assign` on the concerned moves.
        mls = self.env['stock.move.line']
        if updates or 'quantity' in vals:
            next_moves = self.env['stock.move']
            mls = self.filtered(lambda ml: ml.move_id.state == 'done' and ml.product_id.is_storable)
            if not updates:  # we can skip those where quantity is already good up to UoM rounding
                mls = mls.filtered(lambda ml: not ml.product_uom_id.is_zero(ml.quantity - vals['quantity']))
            for ml in mls:
                # undo the original move line
                in_date = ml._synchronize_quant(-ml.quantity_product_uom, ml.location_dest_id, package=ml.result_package_id)[1]
                ml._synchronize_quant(ml.quantity_product_uom, ml.location_id, in_date=in_date)

                # Unreserve and reserve following move in order to have the real reserved quantity on move_line.
                next_moves |= ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))

                # Log a note
                if ml.picking_id:
                    ml._log_message(ml.picking_id, ml, 'stock.track_move_template', vals)
            move_done = mls.move_id
            if move_done:
                move_done._check_quantity()

        # update the date when it seems like (additional) quantities are "done" and the date hasn't been manually updated
        if 'date' not in vals and ('product_uom_id' in vals or 'quantity' in vals or vals.get('picked', False)):
            updated_ml_ids = set()
            for ml in self:
                if ml.state in ['draft', 'cancel', 'done']:
                    continue
                if vals.get('picked', False) and not ml.picked:
                    updated_ml_ids.add(ml.id)
                    continue
                if ('quantity' in vals or 'product_uom_id' in vals) and ml.picked:
                    new_qty = updates.get('product_uom_id', ml.product_uom_id)._compute_quantity(vals.get('quantity', ml.quantity), ml.product_id.uom_id, rounding_method='HALF-UP')
                    old_qty = ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id, rounding_method='HALF-UP')
                    if ml.product_uom_id.compare(old_qty, new_qty) < 0:
                        updated_ml_ids.add(ml.id)
            self.env['stock.move.line'].browse(updated_ml_ids).date = fields.Datetime.now()

        res = super(StockMoveLine, self).write(vals)

        for ml in mls:
            available_qty, dummy = ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id)
            ml._synchronize_quant(ml.quantity_product_uom, ml.location_dest_id, package=ml.result_package_id)
            if available_qty < 0:
                ml._free_reservation(
                    ml.product_id, ml.location_id,
                    abs(available_qty), lot_id=ml.lot_id, package_id=ml.package_id,
                    owner_id=ml.owner_id)

        if packages_to_check:
            # Clear the dest from packages if not linked to any active picking
            packages_to_check.filtered(lambda p: p.package_dest_id and not p.picking_ids).package_dest_id = False
        if updates or 'quantity' in vals:
            # Updated fields could imply that entire packs are no longer entire.
            if mls_to_update := self._get_lines_not_entire_pack():
                mls_to_update.write({'is_entire_pack': False})

        # As stock_account values according to a move's `product_uom_qty`, we consider that any
        # done stock move should have its `quantity_done` equals to its `product_uom_qty`, and
        # this is what move's `action_done` will do. So, we replicate the behavior here.
        if updates or 'quantity' in vals:
            next_moves._do_unreserve()
            next_moves._action_assign()

        if moves_to_recompute_state:
            moves_to_recompute_state._recompute_state()

        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        for ml in self:
            if ml.state in ('done', 'cancel'):
                raise UserError(_(
                    "Deleting product moves after the transfer is done?\n\n"
                    "That would be like going back in time to revert all operations triggered after this move. Who knows what the end result would be, So let's not do it.\n\n"
                    "Try changing the “done” quantity to 0 instead."
                ))

    def unlink(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        for ml in self:
            # Unlinking a move line should unreserve.
            if not float_is_zero(ml.quantity_product_uom, precision_digits=precision) and ml.move_id and not ml.move_id._should_bypass_reservation(ml.location_id):
                self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.quantity_product_uom, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
        moves = self.mapped('move_id')
        packages = self.env['stock.package'].browse(self.result_package_id._get_all_package_dest_ids())
        res = super().unlink()
        if moves:
            # Add with_prefetch() to set the _prefecht_ids = _ids
            # because _prefecht_ids generator look lazily on the cache of move_id
            # which is clear by the unlink of move line
            moves.with_prefetch()._recompute_state()
        if packages:
            # Clear the dest from packages if not linked to any active picking
            packages.filtered(lambda p: p.package_dest_id and not p.picking_ids).package_dest_id = False
        return res

    def _exclude_requiring_lot(self):
        self.ensure_one()
        return self.move_id.picking_type_id or self.is_inventory or self.lot_id or self.move_id.scrap_id

    def _action_done(self):
        """ This method is called during a move's `action_done`. It'll actually move a quant from
        the source location to the destination location, and unreserve if needed in the source
        location.

        This method is intended to be called on all the move lines of a move. This method is not
        intended to be called when editing a `done` move (that's what the override of `write` here
        is done.
        """

        # First, we loop over all the move lines to do a preliminary check: `quantity` should not
        # be negative and, according to the presence of a picking type or a linked inventory
        # adjustment, enforce some rules on the `lot_id` field. If `quantity` is null, we unlink
        # the line. It is mandatory in order to free the reservation and correctly apply
        # `action_done` on the next move lines.
        ml_ids_tracked_without_lot = OrderedSet()
        ml_ids_to_delete = OrderedSet()
        ml_ids_to_create_lot = OrderedSet()
        ml_ids_to_check = defaultdict(OrderedSet)

        for ml in self:
            # Check here if `ml.quantity` respects the rounding of `ml.product_uom_id`.
            uom_qty = ml.product_uom_id.round(ml.quantity, rounding_method='HALF-UP')
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit')
            quantity = float_round(ml.quantity, precision_digits=precision_digits, rounding_method='HALF-UP')
            if float_compare(uom_qty, quantity, precision_digits=precision_digits) != 0:
                raise UserError(_('The quantity done for the product "%(product)s" doesn\'t respect the rounding precision '
                                  'defined on the unit of measure "%(unit)s". Please change the quantity done or the '
                                  'rounding precision of your unit of measure.',
                                  product=ml.product_id.display_name, unit=ml.product_uom_id.name))

            qty_done_float_compared = ml.product_uom_id.compare(ml.quantity, 0)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking == 'none':
                    continue
                picking_type_id = ml.move_id.picking_type_id
                if not ml._exclude_requiring_lot():
                    ml_ids_tracked_without_lot.add(ml.id)
                    continue
                if not picking_type_id or ml.lot_id or (not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots):
                    # If the user disabled both `use_create_lots` and `use_existing_lots`
                    # checkboxes on the picking type, he's allowed to enter tracked
                    # products without a `lot_id`.
                    continue
                if picking_type_id.use_create_lots:
                    ml_ids_to_check[(ml.product_id, ml.company_id)].add(ml.id)
                else:
                    ml_ids_tracked_without_lot.add(ml.id)

            elif qty_done_float_compared < 0:
                raise UserError(_('No negative quantities allowed'))
            elif not ml.is_inventory:
                ml_ids_to_delete.add(ml.id)

        for (product, _company), mls in ml_ids_to_check.items():
            mls = self.env['stock.move.line'].browse(mls)
            lots = self.env['stock.lot'].search([
                '|', ('company_id', '=', False), ('company_id', '=', ml.company_id.id),
                ('product_id', '=', product.id),
                ('name', 'in', mls.mapped('lot_name')),
            ])
            lots = {lot.name: lot for lot in lots}
            for ml in mls:
                lot = lots.get(ml.lot_name)
                if lot:
                    ml.lot_id = lot.id
                elif ml.lot_name:
                    ml_ids_to_create_lot.add(ml.id)
                else:
                    ml_ids_tracked_without_lot.add(ml.id)

        if ml_ids_tracked_without_lot:
            mls_tracked_without_lot = self.env['stock.move.line'].browse(ml_ids_tracked_without_lot)
            products_list = "\n".join(f"- {product_name}" for product_name in mls_tracked_without_lot.mapped("product_id.display_name"))
            raise UserError(
                _(
                    "You need to supply a Lot/Serial Number for product:\n%(products)s",
                    products=products_list,
                ),
            )
        if ml_ids_to_create_lot:
            self.env['stock.move.line'].browse(ml_ids_to_create_lot)._create_and_assign_production_lot()

        mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
        mls_to_delete.unlink()

        mls_todo = (self - mls_to_delete)
        mls_todo._check_company()

        # Now, we can actually move the quant.
        ml_ids_to_ignore = OrderedSet()
        quants_cache = self.env['stock.quant']._get_quants_by_products_locations(
            mls_todo.product_id, mls_todo.location_id | mls_todo.location_dest_id,
            extra_domain=['|', ('lot_id', 'in', mls_todo.lot_id.ids), ('lot_id', '=', False)])

        # Prepare package history records before any actual move
        if not self.env.context.get('ignore_dest_packages'):
            package_history_vals = mls_todo._prepare_package_history_vals()
            if package_history_vals:
                self.env['stock.package.history'].create(package_history_vals)

        for ml in mls_todo.with_context(quants_cache=quants_cache):
            # if this move line is force assigned, unreserve elsewhere if needed
            ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, action="reserved")
            available_qty, in_date = ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id)
            ml._synchronize_quant(ml.quantity_product_uom, ml.location_dest_id, package=ml.result_package_id, in_date=in_date)
            if available_qty < 0:
                ml.with_context(quants_cache=None)._free_reservation(
                    ml.product_id, ml.location_id,
                    abs(available_qty), lot_id=ml.lot_id, package_id=ml.package_id,
                    owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
            ml_ids_to_ignore.add(ml.id)

        if not self.env.context.get('ignore_dest_packages'):
            mls_todo.result_package_id._apply_dest_to_package()

        # Reset the reserved quantity as we just moved it to the destination location.
        mls_todo.write({
            'date': fields.Datetime.now(),
        })

    def _synchronize_quant(self, quantity, location, action="available", in_date=False, **quants_value):
        """ quantity should be express in product's UoM"""
        lot = quants_value.get('lot', self.lot_id)
        package = quants_value.get('package', self.package_id)
        owner = quants_value.get('owner', self.owner_id)
        available_qty = 0
        if not self.product_id.is_storable or self.product_uom_id.is_zero(quantity):
            return 0, False
        if action == "available":
            available_qty, in_date = self.env['stock.quant']._update_available_quantity(self.product_id, location, quantity, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date)
        elif action == "reserved" and not self.move_id._should_bypass_reservation(location):
            self.env['stock.quant']._update_reserved_quantity(self.product_id, location, quantity, lot_id=lot, package_id=package, owner_id=owner)
        if available_qty < 0 and lot:
            # see if we can compensate the negative quants with some untracked quants
            untracked_qty = self.env['stock.quant']._get_available_quantity(self.product_id, location, lot_id=False, package_id=package, owner_id=owner, strict=True)
            if not untracked_qty:
                return available_qty, in_date
            taken_from_untracked_qty = min(untracked_qty, abs(quantity))
            self.env['stock.quant']._update_available_quantity(self.product_id, location, -taken_from_untracked_qty, lot_id=False, package_id=package, owner_id=owner, in_date=in_date)
            self.env['stock.quant']._update_available_quantity(self.product_id, location, taken_from_untracked_qty, lot_id=lot, package_id=package, owner_id=owner, in_date=in_date)
        return available_qty, in_date

    def _get_similar_move_lines(self):
        self.ensure_one()
        lines = self.env['stock.move.line']
        picking_id = self.move_id.picking_id if self.move_id else self.picking_id
        if picking_id:
            lines |= picking_id.move_line_ids.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        return lines

    def _prepare_new_lot_vals(self):
        self.ensure_one()
        vals =  {
            'name': self.lot_name,
            'product_id': self.product_id.id,
        }
        if self.product_id.company_id and self.company_id in (self.product_id.company_id.all_child_ids | self.product_id.company_id):
            vals['company_id'] = self.company_id.id
        return vals

    def _create_and_assign_production_lot(self):
        """ Creates and assign new production lots for move lines."""
        lot_vals = []
        # It is possible to have multiple time the same lot to create & assign,
        # so we handle the case with 2 dictionaries.
        key_to_index = {}  # key to index of the lot
        key_to_mls = defaultdict(lambda: self.env['stock.move.line'])  # key to all mls
        for ml in self:
            key = (ml.product_id.id, ml.lot_name)
            key_to_mls[key] |= ml
            if ml.tracking != 'lot' or key not in key_to_index:
                key_to_index[key] = len(lot_vals)
                lot_vals.append(ml._prepare_new_lot_vals())

        lots = self.env['stock.lot'].create(lot_vals)
        for key, mls in key_to_mls.items():
            lot = lots[key_to_index[key]].with_prefetch(lots._ids)   # With prefetch to reconstruct the ones broke by accessing by index
            mls.with_prefetch(self._prefetch_ids).write({'lot_id': lot.id})

    def _log_message(self, record, move, template, vals):
        data = vals.copy()
        if 'lot_id' in vals and vals['lot_id'] != move.lot_id.id:
            data['lot_name'] = self.env['stock.lot'].browse(vals.get('lot_id')).name
        if 'location_id' in vals:
            data['location_name'] = self.env['stock.location'].browse(vals.get('location_id')).name
        if 'location_dest_id' in vals:
            data['location_dest_name'] = self.env['stock.location'].browse(vals.get('location_dest_id')).name
        if 'package_id' in vals and vals['package_id'] != move.package_id.id:
            data['package_name'] = self.env['stock.package'].browse(vals.get('package_id')).name
        if 'package_result_id' in vals and vals['package_result_id'] != move.package_result_id.id:
            data['result_package_dest_name'] = self.env['stock.package'].browse(vals.get('result_package_id')).name
        if 'owner_id' in vals and vals['owner_id'] != move.owner_id.id:
            data['owner_name'] = self.env['res.partner'].browse(vals.get('owner_id')).name
        record.message_post_with_source(
            template,
            render_values={'move': move, 'vals': dict(vals, **data)},
            subtype_xmlid='mail.mt_note',
        )

    def _free_reservation(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, ml_ids_to_ignore=None):
        """ When editing a done move line or validating one with some forced quantities, it is
        possible to impact quants that were not reserved. It is therefore necessary to edit or
        unlink the move lines that reserved a quantity now unavailable.

        :param ml_ids_to_ignore: OrderedSet of `stock.move.line` ids that should NOT be unreserved
        """
        self.ensure_one()
        if ml_ids_to_ignore is None:
            ml_ids_to_ignore = OrderedSet()
        ml_ids_to_ignore |= self.ids

        if self.move_id._should_bypass_reservation(location_id):
            return

        # We now have to find the move lines that reserved our now unavailable quantity. We
        # take care to exclude ourselves and the move lines were work had already been done.
        outdated_move_lines_domain = [
            ('state', 'not in', ['done', 'cancel']),
            ('product_id', '=', product_id.id),
            ('lot_id', '=', lot_id.id if lot_id else False),
            ('location_id', '=', location_id.id),
            ('owner_id', '=', owner_id.id if owner_id else False),
            ('package_id', '=', package_id.id if package_id else False),
            ('quantity_product_uom', '>', 0.0),
            ('picked', '=', False),
            ('id', 'not in', tuple(ml_ids_to_ignore)),
        ]

        # We take the current picking first, then the pickings with the latest scheduled date
        def current_picking_first(cand):
            return (
                cand.picking_id != self.move_id.picking_id,
                -(cand.picking_id.scheduled_date or cand.move_id.date).timestamp()
                if cand.picking_id or cand.move_id else 0,
                -cand.id)

        outdated_candidates = self.env['stock.move.line'].search(outdated_move_lines_domain).sorted(current_picking_first)

        # As the move's state is not computed over the move lines, we'll have to manually
        # recompute the moves which we adapted their lines.
        move_to_reassign = self.env['stock.move']
        to_unlink_candidate_ids = set()

        for candidate in outdated_candidates:
            move_to_reassign |= candidate.move_id
            if self.product_uom_id.compare(candidate.quantity_product_uom, quantity) <= 0:
                quantity -= candidate.quantity_product_uom
                to_unlink_candidate_ids.add(candidate.id)
                if self.product_uom_id.is_zero(quantity):
                    break
            else:
                candidate.quantity -= candidate.product_id.uom_id._compute_quantity(quantity, candidate.product_uom_id, rounding_method='HALF-UP')
                break

        move_line_to_unlink = self.env['stock.move.line'].browse(to_unlink_candidate_ids)
        for m in (move_line_to_unlink.move_id | move_to_reassign):
            m.write({
                'procure_method': 'make_to_stock',
                'move_orig_ids': [Command.clear()]
            })
        move_line_to_unlink.unlink()
        move_to_reassign._action_assign()

    def _get_aggregated_properties(self, move_line=False, move=False):
        move = move or move_line.move_id
        uom = move.product_uom or move_line.product_uom_id
        packaging_uom = move.packaging_uom_id
        name = move.product_id.display_name
        description = move.description_picking or ""
        product = move.product_id
        if description.startswith(name):
            description = description.removeprefix(name).strip()
        elif description.startswith(product.name):
            description = description.removeprefix(product.name).strip()
        line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}'
        properties = {
            'line_key': line_key,
            'name': name,
            'description': description,
            'product_uom': uom,
            'packaging_uom_id': packaging_uom,
            'move': move,
        }
        if move_line and move_line.result_package_id:
            properties['package'] = move_line.result_package_id
            properties['package_history'] = move_line.package_history_id
            properties['line_key'] += f'_{move_line.result_package_id.id}'
        return properties

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, quantity, product_uom}, ...}
        """
        aggregated_move_lines = {}

        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids

        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            aggregated_properties = self._get_aggregated_properties(move_line=move_line)
            line_key, uom = aggregated_properties['line_key'], aggregated_properties['product_uom']
            quantity = move_line.product_uom_id._compute_quantity(move_line.quantity, uom)
            packaging_quantity = move_line.product_uom_id._compute_quantity(quantity, move_line.move_id.packaging_uom_id)
            if line_key not in aggregated_move_lines:
                qty_ordered = None
                packaging_qty_ordered = None
                if backorders and not kwargs.get('strict'):
                    qty_ordered = move_line.move_id.product_uom_qty
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: line_key.startswith(self._get_aggregated_properties(move=ml.move_id)['line_key'])
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                    # Remove the done quantities of the other move lines of the stock move
                    previous_move_lines = move_line.move_id.move_line_ids.filtered(
                        lambda ml: line_key.startswith(self._get_aggregated_properties(move=ml.move_id)['line_key']) and ml.id != move_line.id
                    )
                    qty_ordered -= sum([m.product_uom_id._compute_quantity(m.quantity, uom) for m in previous_move_lines])
                    packaging_qty_ordered = move_line.product_uom_id._compute_quantity(qty_ordered, move_line.move_id.packaging_uom_id)
                aggregated_move_lines[line_key] = {
                    **aggregated_properties,
                    'quantity': quantity,
                    'packaging_quantity': packaging_quantity,
                    'qty_ordered': qty_ordered or quantity,
                    'packaging_qty_ordered': packaging_qty_ordered or packaging_quantity,
                    'product': move_line.product_id,
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += quantity
                aggregated_move_lines[line_key]['packaging_qty_ordered'] += packaging_quantity
                aggregated_move_lines[line_key]['quantity'] += quantity
                aggregated_move_lines[line_key]['packaging_quantity'] += packaging_quantity

        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        if kwargs.get('strict'):
            return aggregated_move_lines
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_ids:
            to_bypass = False
            if not (empty_move.product_uom_qty and empty_move.product_uom.is_zero(empty_move.quantity)):
                continue
            if empty_move.state != "cancel":
                if empty_move.state != "confirmed" or empty_move.move_line_ids:
                    continue
                else:
                    to_bypass = True
            aggregated_properties = self._get_aggregated_properties(move=empty_move)
            line_key = aggregated_properties['line_key']

            if not any(aggregated_key.startswith(line_key) for aggregated_key in aggregated_move_lines) and not to_bypass:
                qty_ordered = empty_move.product_uom_qty
                aggregated_move_lines[line_key] = {
                    **aggregated_properties,
                    'quantity': False,
                    'qty_ordered': qty_ordered,
                    'product': empty_move.product_id,
                }
            elif line_key in aggregated_move_lines:
                aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty
            else:
                keys = list(filter(lambda key: key.startswith(line_key), aggregated_move_lines))
                if keys:
                    aggregated_move_lines[keys[0]]['qty_ordered'] += empty_move.product_uom_qty

        return aggregated_move_lines

    def _compute_sale_price(self):
        # To Override
        pass

    def _prepare_package_history_vals(self):
        history_vals = []
        packages = self.env['stock.package'].browse(self.result_package_id._get_all_package_dest_ids())
        for package in packages:
            history_vals.append({
                'location_id': package.location_id.id,
                'location_dest_id': package.location_dest_id.id,
                'move_line_ids': [Command.set(package.move_line_ids.filtered(lambda ml: ml.result_package_id == package).ids)],
                'picking_ids': [Command.set(package.picking_ids.ids)],
                'package_id': package.id,
                'package_name': package.complete_name,
                'parent_orig_id': package.parent_package_id.id,
                'parent_orig_name': package.parent_package_id.complete_name,
                'parent_dest_id': package.package_dest_id.id,
                'parent_dest_name': package.package_dest_id.dest_complete_name,
                'outermost_dest_id': package.outermost_package_id.id or package.id,
            })

        return history_vals

    @api.model
    def _prepare_stock_move_vals(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'product_uom_qty': 0 if self.picking_id and self.picking_id.state != 'done' else self.quantity,
            'product_uom': self.product_uom_id.id,
            'location_id': self.picking_id.location_id.id,
            'location_dest_id': self.picking_id.location_dest_id.id,
            'picked': self.picked,
            'picking_id': self.picking_id.id,
            'state': self.picking_id.state,
            'picking_type_id': self.picking_id.picking_type_id.id,
            'restrict_partner_id': self.picking_id.owner_id.id,
            'company_id': self.picking_id.company_id.id,
            'partner_id': self.picking_id.partner_id.id,
        }

    def _copy_quant_info(self, vals):
        quant = self.env['stock.quant'].browse(vals.get('quant_id', 0))
        line_data = {
            'product_id': quant.product_id.id,
            'lot_id': quant.lot_id.id,
            'package_id': quant.package_id.id,
            'location_id': quant.location_id.id,
            'owner_id': quant.owner_id.id,
        }
        return line_data

    def action_open_reference(self):
        self.ensure_one()
        if self.move_id:
            action = self.move_id.action_open_reference()
            if action['res_model'] != 'stock.move':
                return action
        return {
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.id,
        }

    def _pre_put_in_pack_hook(self, all_lines=False, package_id=False, package_type_id=False, package_name=False, from_package_wizard=False):
        move_lines = all_lines if self.env.context.get('force_move_lines') and all_lines else self
        action = move_lines._check_destinations()
        if action:
            return action
        if self._should_display_put_in_pack_wizard(package_id, package_type_id, package_name, from_package_wizard):
            action = self.env["ir.actions.actions"]._for_xml_id("stock.action_put_in_pack_wizard")
            action['context'] = {
                **literal_eval(action.get('context', '{}')),
                'all_move_line_ids': move_lines.ids,
                'default_move_line_ids': self.ids,
                'default_location_dest_id': self.location_dest_id.id,
            }
            return action

    def _check_destinations(self):
        if len(self.location_dest_id) > 1:
            view_id = self.env.ref('stock.stock_package_destination_form_view').id
            wiz = self.env['stock.package.destination'].create({
                'move_line_ids': self.ids,
                'location_dest_id': self[0].location_dest_id.id,
            })
            return {
                'name': _('Choose destination location'),
                'view_mode': 'form',
                'res_model': 'stock.package.destination',
                'view_id': view_id,
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': wiz.id,
                'target': 'new'
            }

    def _get_lines_not_entire_pack(self):
        """ Checks within self for move lines that should no longer be considered as entire packs.
        """
        relevant_move_lines = self.filtered(lambda ml: ml.is_entire_pack)
        if not relevant_move_lines:
            return False

        # If `result_package_id` was either removed or changed, cannot be considered as an entire pack anymore.
        ids_to_update = set(relevant_move_lines.filtered(lambda ml: ml.package_id != ml.result_package_id).ids)
        for package, move_lines in relevant_move_lines.grouped('package_id').items():
            pickings = move_lines.picking_id
            if not pickings._is_single_transfer() or not pickings._check_move_lines_map_quant_package(package):
                ids_to_update.update(pickings.move_line_ids.filtered(lambda ml: ml.package_id == package).ids)

        return self.env['stock.move.line'].browse(ids_to_update)

    def _put_in_pack(self, package_id=False, package_type_id=False, package_name=False):
        if package_id:
            package = self.env['stock.package'].browse(package_id)
        elif package_type_id:
            package = self.env['stock.package'].create({
                'name': package_name,
                'package_type_id': package_type_id,
            })
        else:
            package_vals = {'name': package_name}
            package_type = self.move_id.packaging_uom_id.package_type_id
            if len(package_type) == 1:
                package_vals['package_type_id'] = package_type.id
            package = self.env['stock.package'].create(package_vals)
        if len(self) == 1:
            default_dest_location = self._get_default_dest_location()
            self.location_dest_id = default_dest_location._get_putaway_strategy(
                product=self.product_id,
                quantity=self.quantity,
                package=package
            )
        self.write({'result_package_id': package.id})
        return package

    def _post_put_in_pack_hook(self, package):
        if package and self.picking_type_id.auto_print_package_label:
            if self.picking_type_id.package_label_to_print == 'pdf':
                action = self.env.ref("stock.action_report_package_barcode_small").report_action(package.id, config=False)
            elif self.picking_type_id.package_label_to_print == 'zpl':
                action = self.env.ref("stock.label_package_template").report_action(package.id, config=False)
            if action:
                action.update({'close_on_report_download': True})
                clean_action(action, self.env)
                return action
        return package

    def _to_pack(self, without_pack=True):
        if len(self.picking_type_id) > 1:
            raise UserError(_('You cannot pack products into the same package when they are from different transfers with different operation types'))
        quantity_move_line_ids = self.filtered(
            lambda ml: ml.product_uom_id.compare(ml.quantity, 0.0) > 0 and (without_pack != bool(ml.result_package_id))
            and ml.state not in ('done', 'cancel')
        )
        move_line_ids = quantity_move_line_ids.filtered(lambda ml: ml.picked)
        if not move_line_ids:
            move_line_ids = quantity_move_line_ids
        return move_line_ids

    def action_put_in_pack(self, *, package_id=False, package_type_id=False, package_name=False):
        move_lines = self
        if self.env.context.get('all_move_line_ids'):
            move_lines = self.env['stock.move.line'].browse(self.env.context['all_move_line_ids'])
        move_lines_to_pack = move_lines._to_pack()
        done_pack = False
        if move_lines_to_pack:
            action = move_lines_to_pack._pre_put_in_pack_hook(move_lines, package_id, package_type_id, package_name, self.env.context.get('from_package_wizard'))
            if action:
                return action

            package = move_lines_to_pack._put_in_pack(package_id, package_type_id, package_name)
            done_pack = move_lines_to_pack._post_put_in_pack_hook(package)
        if done_pack and not self.env.context.get('force_move_lines'):
            return done_pack
        elif lines_with_pack_to_pack := move_lines._to_pack(without_pack=False):
            packs_to_pack = lines_with_pack_to_pack.result_package_id.mapped(lambda p: p.outermost_package_id or p)
            if done_pack:
                packs_to_pack = packs_to_pack.filtered(lambda p: p.id != done_pack.id)
                package_id = done_pack.id
            if packs_to_pack:
                return packs_to_pack.action_put_in_pack(package_id=package_id, package_type_id=package_type_id, package_name=package_name)
        if not done_pack:
            raise UserError(_("There is nothing eligible to put in a pack. Either there are no quantities to put in a pack or moves are already done."))

    def _get_revert_inventory_move_values(self):
        self.ensure_one()
        return {
            'inventory_name': _('%s [reverted]', self.reference),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.quantity,
            'company_id': self.company_id.id or self.env.company.id,
            'state': 'confirmed',
            'location_id': self.location_dest_id.id,
            'location_dest_id': self.location_id.id,
            'is_inventory': True,
            'picked': True,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'quantity': self.quantity,
                'location_id': self.location_dest_id.id,
                'location_dest_id': self.location_id.id,
                'company_id': self.company_id.id or self.env.company.id,
                'lot_id': self.lot_id.id,
                'package_id': self.package_id.id,
                'result_package_id': self.package_id.id,
                'owner_id': self.owner_id.id,
            })]
        }

    def action_revert_inventory(self):
        move_vals = []
        # remove inventory mode
        self = self.with_context(inventory_mode=False)
        processed_move_line = self.env['stock.move.line']
        for move_line in self:
            if move_line.is_inventory and not move_line.product_uom_id.is_zero(move_line.quantity):
                processed_move_line += move_line
                move_vals.append(move_line._get_revert_inventory_move_values())
        if not processed_move_line:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("There are no inventory adjustments to revert."),
                }
            }
        moves = self.env['stock.move'].create(move_vals)
        moves._action_done()
        return {
            'name': _('Reverted Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'list',
            'domain': [('id', 'in', moves.move_line_ids.ids + self.ids)]
        }

    def _get_linkable_moves(self):
        self.ensure_one()
        moves = self.picking_id.move_ids.filtered(lambda x: x.product_id == self.product_id)
        return sorted(moves, key=lambda m: m.quantity < m.product_qty, reverse=True)

    def _should_display_put_in_pack_wizard(self, package_id, package_type_id, package_name, from_package_wizard):
        define_package_type = self._should_set_package()
        return define_package_type and not from_package_wizard and (not package_id and not package_type_id and not package_name)

    def _should_set_package(self):
        package_type = self.picking_id.picking_type_id
        return len(package_type) == 1 and package_type.set_package_type
