# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter, defaultdict

from odoo import _, api, fields, tools, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import OrderedSet, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _description = "Product Moves (Stock Move Line)"
    _rec_name = "product_id"
    _order = "result_package_id desc, id"

    picking_id = fields.Many2one(
        'stock.picking', 'Transfer', auto_join=True,
        check_company=True,
        index=True,
        help='The stock operation where the packing has been made')
    move_id = fields.Many2one(
        'stock.move', 'Stock Operation',
        check_company=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True, index=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade", check_company=True, domain="[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]",
        compute="_compute_product_uom_id", store=True, readonly=False, precompute=True,
    )
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_category_name = fields.Char(related="product_id.categ_id.complete_name", store=True, string="Product Category")
    reserved_qty = fields.Float(
        'Real Reserved Quantity', digits=0, copy=False,
        compute='_compute_reserved_qty', inverse='_set_reserved_qty', store=True)
    reserved_uom_qty = fields.Float(
        'Reserved', default=0.0, digits='Product Unit of Measure', required=True, copy=False)
    qty_done = fields.Float('Done', default=0.0, digits='Product Unit of Measure', copy=False)
    package_id = fields.Many2one(
        'stock.quant.package', 'Source Package', ondelete='restrict',
        check_company=True,
        domain="[('location_id', '=', location_id)]")
    package_level_id = fields.Many2one('stock.package_level', 'Package Level', check_company=True)
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    lot_name = fields.Char('Lot/Serial Number Name')
    result_package_id = fields.Many2one(
        'stock.quant.package', 'Destination Package',
        ondelete='restrict', required=False, check_company=True,
        domain="['|', '|', ('location_id', '=', False), ('location_id', '=', location_dest_id), ('id', '=', package_id)]",
        help="If set, the operations are packed into this package")
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    owner_id = fields.Many2one(
        'res.partner', 'From Owner',
        check_company=True,
        help="When validating the transfer, the products will be taken from this owner.")
    location_id = fields.Many2one(
        'stock.location', 'From', domain="[('usage', '!=', 'view')]", check_company=True, required=True,
        compute="_compute_location_id", store=True, readonly=False, precompute=True,
    )
    location_dest_id = fields.Many2one('stock.location', 'To', domain="[('usage', '!=', 'view')]", check_company=True, required=True, compute="_compute_location_id", store=True, readonly=False, precompute=True)
    location_usage = fields.Selection(string="Source Location Type", related='location_id.usage')
    location_dest_usage = fields.Selection(string="Destination Location Type", related='location_dest_id.usage')
    lots_visible = fields.Boolean(compute='_compute_lots_visible')
    picking_partner_id = fields.Many2one(related='picking_id.partner_id', readonly=True)
    picking_code = fields.Selection(related='picking_id.picking_type_id.code', readonly=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation type', compute='_compute_picking_type_id', search='_search_picking_type_id')
    picking_type_use_create_lots = fields.Boolean(related='picking_id.picking_type_id.use_create_lots', readonly=True)
    picking_type_use_existing_lots = fields.Boolean(related='picking_id.picking_type_id.use_existing_lots', readonly=True)
    picking_type_entire_packs = fields.Boolean(related='picking_id.picking_type_id.show_entire_packs', readonly=True)
    state = fields.Selection(related='move_id.state', store=True, related_sudo=False)
    is_initial_demand_editable = fields.Boolean(related='move_id.is_initial_demand_editable')
    is_inventory = fields.Boolean(related='move_id.is_inventory')
    is_locked = fields.Boolean(related='move_id.is_locked', readonly=True)
    consume_line_ids = fields.Many2many('stock.move.line', 'stock_move_line_consume_rel', 'consume_line_id', 'produce_line_id')
    produce_line_ids = fields.Many2many('stock.move.line', 'stock_move_line_consume_rel', 'produce_line_id', 'consume_line_id')
    reference = fields.Char(related='move_id.reference', store=True, related_sudo=False, readonly=False)
    tracking = fields.Selection(related='product_id.tracking', readonly=True)
    origin = fields.Char(related='move_id.origin', string='Source')
    description_picking = fields.Text(string="Description picking")

    @api.depends('product_uom_id.category_id', 'product_id.uom_id.category_id', 'move_id.product_uom', 'product_id.uom_id')
    def _compute_product_uom_id(self):
        for line in self:
            if not line.product_uom_id or line.product_uom_id.category_id != line.product_id.uom_id.category_id:
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

    @api.depends('picking_id')
    def _compute_picking_type_id(self):
        self.picking_type_id = False
        for line in self:
            if line.picking_id:
                line.picking_type_id = line.picking_id.picking_type_id

    @api.depends('move_id', 'move_id.location_id', 'move_id.location_dest_id')
    def _compute_location_id(self):
        for line in self:
            if not line.location_id:
                line.location_id = line.move_id.location_id or line.picking_id.location_id
            if not line.location_dest_id:
                line.location_dest_id = line.move_id.location_dest_id or line.picking_id.location_dest_id

    def _search_picking_type_id(self, operator, value):
        return [('picking_id.picking_type_id', operator, value)]

    @api.depends('product_id', 'product_uom_id', 'reserved_uom_qty')
    def _compute_reserved_qty(self):
        for line in self:
            line.reserved_qty = line.product_uom_id._compute_quantity(line.reserved_uom_qty, line.product_id.uom_id, rounding_method='HALF-UP')

    def _set_reserved_qty(self):
        """ The meaning of reserved_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `reserved_qty`, where the same write should set the `reserved_uom_qty` field instead, in order to
        detect errors. """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `reserved_qty` field instead of the `reserved_uom_qty`.'))

    @api.constrains('lot_id', 'product_id')
    def _check_lot_product(self):
        for line in self:
            if line.lot_id and line.product_id != line.lot_id.sudo().product_id:
                raise ValidationError(_(
                    'This lot %(lot_name)s is incompatible with this product %(product_name)s',
                    lot_name=line.lot_id.name,
                    product_name=line.product_id.display_name
                ))

    @api.constrains('reserved_uom_qty')
    def _check_reserved_done_quantity(self):
        for move_line in self:
            if move_line.state == 'done' and not float_is_zero(move_line.reserved_uom_qty, precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure')):
                raise ValidationError(_('A done move line should never have a reserved quantity.'))

    @api.constrains('qty_done')
    def _check_positive_qty_done(self):
        if any(ml.qty_done < 0 for ml in self):
            raise ValidationError(_('You can not enter negative quantities.'))

    @api.onchange('product_id', 'product_uom_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.picking_id:
                product = self.product_id.with_context(lang=self.picking_id.partner_id.lang or self.env.user.lang)
                self.description_picking = product._get_description(self.picking_id.picking_type_id)
            self.lots_visible = self.product_id.tracking != 'none'

    @api.onchange('lot_name', 'lot_id')
    def _onchange_serial_number(self):
        """ When the user is encoding a move line for a tracked product, we apply some logic to
        help him. This includes:
            - automatically switch `qty_done` to 1.0
            - warn if he has already encoded `lot_name` in another move line
            - warn (and update if appropriate) if the SN is in a different source location than selected
        """
        res = {}
        if self.product_id.tracking == 'serial':
            if not self.qty_done:
                self.qty_done = 1

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
                                                                        ('company_id', '=', self.company_id.id)])
                        quants = lots.quant_ids.filtered(lambda q: q.quantity != 0 and q.location_id.usage in ['customer', 'internal', 'transit'])
                        if quants:
                            message = _('Serial number (%s) already exists in location(s): %s. Please correct the serial number encoded.', self.lot_name, ', '.join(quants.location_id.mapped('display_name')))
                elif self.lot_id:
                    counter = Counter([line.lot_id.id for line in move_lines_to_check])
                    if counter.get(self.lot_id.id) and counter[self.lot_id.id] > 1:
                        message = _('You cannot use the same serial number twice. Please correct the serial numbers encoded.')
                    else:
                        # check if in correct source location
                        message, recommended_location = self.env['stock.quant'].sudo()._check_serial_number(self.product_id,
                                                                                                     self.lot_id,
                                                                                                     self.company_id,
                                                                                                     self.location_id,
                                                                                                     self.picking_id.location_id)
                        if recommended_location:
                            self.location_id = recommended_location
            if message:
                res['warning'] = {'title': _('Warning'), 'message': message}
        return res

    @api.onchange('qty_done', 'product_uom_id')
    def _onchange_qty_done(self):
        """ When the user is encoding a move line for a tracked product, we apply some logic to
        help him. This onchange will warn him if he set `qty_done` to a non-supported value.
        """
        res = {}
        if self.qty_done and self.product_id.tracking == 'serial':
            qty_done = self.product_uom_id._compute_quantity(self.qty_done, self.product_id.uom_id)
            if float_compare(qty_done, 1.0, precision_rounding=self.product_id.uom_id.rounding) != 0:
                message = _('You can only process 1.0 %s of products with unique serial number.', self.product_id.uom_id.name)
                res['warning'] = {'title': _('Warning'), 'message': message}
        return res

    @api.onchange('result_package_id', 'product_id', 'product_uom_id', 'qty_done')
    def _onchange_putaway_location(self):
        default_dest_location = self._get_default_dest_location()
        if not self.id and self.user_has_groups('stock.group_stock_multi_locations') and self.product_id and self.qty_done \
                and self.location_dest_id == default_dest_location:
            qty_done = self.product_uom_id._compute_quantity(self.qty_done, self.product_id.uom_id)
            self.location_dest_id = default_dest_location.with_context(exclude_sml_ids=self.ids)._get_putaway_strategy(
                self.product_id, quantity=qty_done, package=self.result_package_id,
                packaging=self.move_id.product_packaging_id)

    def _apply_putaway_strategy(self):
        if self._context.get('avoid_putaway_rules'):
            return
        self = self.with_context(do_not_unreserve=True)
        for package, smls in groupby(self, lambda sml: sml.result_package_id):
            smls = self.env['stock.move.line'].concat(*smls)
            excluded_smls = set(smls.ids)
            if package.package_type_id:
                best_loc = smls.move_id.location_dest_id.with_context(exclude_sml_ids=excluded_smls, products=smls.product_id)._get_putaway_strategy(self.env['product.product'], package=package)
                smls.location_dest_id = smls.package_level_id.location_dest_id = best_loc
            elif package:
                used_locations = set()
                for sml in smls:
                    if len(used_locations) > 1:
                        break
                    sml.location_dest_id = sml.move_id.location_dest_id.with_context(exclude_sml_ids=excluded_smls)._get_putaway_strategy(sml.product_id, quantity=sml.reserved_uom_qty)
                    excluded_smls.discard(sml.id)
                    used_locations.add(sml.location_dest_id)
                if len(used_locations) > 1:
                    smls.location_dest_id = smls.move_id.location_dest_id
                else:
                    smls.package_level_id.location_dest_id = smls.location_dest_id
            else:
                for sml in smls:
                    qty = max(sml.reserved_uom_qty, sml.qty_done)
                    putaway_loc_id = sml.move_id.location_dest_id.with_context(exclude_sml_ids=excluded_smls)._get_putaway_strategy(
                        sml.product_id, quantity=qty, packaging=sml.move_id.product_packaging_id,
                    )
                    if putaway_loc_id != sml.location_dest_id:
                        sml.location_dest_id = putaway_loc_id
                    excluded_smls.discard(sml.id)

    def _get_default_dest_location(self):
        if not self.user_has_groups('stock.group_stock_storage_categories'):
            return self.location_dest_id[:1]
        if self.env.context.get('default_location_dest_id'):
            return self.env['stock.location'].browse([self.env.context.get('default_location_dest_id')])
        return (self.move_id.location_dest_id or self.picking_id.location_dest_id or self.location_dest_id)[0]

    def _get_putaway_additional_qty(self):
        addtional_qty = {}
        for ml in self._origin:
            qty = max(ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id), ml.reserved_uom_qty)
            addtional_qty[ml.location_dest_id.id] = addtional_qty.get(ml.location_dest_id.id, 0) - qty
        return addtional_qty

    def init(self):
        if not tools.index_exists(self._cr, 'stock_move_line_free_reservation_index'):
            self._cr.execute("""
                CREATE INDEX stock_move_line_free_reservation_index
                ON
                    stock_move_line (id, company_id, product_id, lot_id, location_id, owner_id, package_id)
                WHERE
                    (state IS NULL OR state NOT IN ('cancel', 'done')) AND reserved_qty > 0""")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('move_id'):
                vals['company_id'] = self.env['stock.move'].browse(vals['move_id']).company_id.id
            elif vals.get('picking_id'):
                vals['company_id'] = self.env['stock.picking'].browse(vals['picking_id']).company_id.id

        mls = super().create(vals_list)

        def create_move(move_line):
            new_move = self.env['stock.move'].create(move_line._prepare_stock_move_vals())
            move_line.move_id = new_move.id

        # If the move line is directly create on the picking view.
        # If this picking is already done we should generate an
        # associated done move.
        for move_line in mls:
            if move_line.move_id or not move_line.picking_id:
                continue
            if move_line.picking_id.state != 'done':
                moves = move_line.picking_id.move_ids.filtered(lambda x: x.product_id == move_line.product_id)
                moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
                if moves:
                    move_line.move_id = moves[0].id
                else:
                    create_move(move_line)
            else:
                create_move(move_line)

        moves_to_update = mls.filtered(
            lambda ml:
            ml.move_id and
            ml.qty_done and (
                ml.move_id.state == 'done' or (
                    ml.move_id.picking_id and
                    ml.move_id.picking_id.immediate_transfer
                ))
        ).move_id
        for move in moves_to_update:
            move.with_context(avoid_putaway_rules=True).product_uom_qty = move.quantity_done

        for ml, vals in zip(mls, vals_list):
            if self.env.context.get('import_file') and ml.reserved_uom_qty and not ml.move_id._should_bypass_reservation():
                raise UserError(_("It is not allowed to import reserved quantity, you have to use the quantity directly."))

            if ml.state == 'done':
                if ml.product_id.type == 'product':
                    Quant = self.env['stock.quant']
                    quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id,rounding_method='HALF-UP')
                    in_date = None
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
        return mls

    def write(self, vals):
        if self.env.context.get('bypass_reservation_update'):
            return super(StockMoveLine, self).write(vals)

        if 'product_id' in vals and any(vals.get('state', ml.state) != 'draft' and vals['product_id'] != ml.product_id.id for ml in self):
            raise UserError(_("Changing the product is only allowed in 'Draft' state."))

        moves_to_recompute_state = self.env['stock.move']
        Quant = self.env['stock.quant']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        triggers = [
            ('location_id', 'stock.location'),
            ('location_dest_id', 'stock.location'),
            ('lot_id', 'stock.lot'),
            ('package_id', 'stock.quant.package'),
            ('result_package_id', 'stock.quant.package'),
            ('owner_id', 'res.partner'),
            ('product_uom_id', 'uom.uom')
        ]
        updates = {}
        for key, model in triggers:
            if key in vals:
                updates[key] = vals[key] if isinstance(vals[key], models.BaseModel) else self.env[model].browse(vals[key])

        if 'result_package_id' in updates:
            for ml in self.filtered(lambda ml: ml.package_level_id):
                if updates.get('result_package_id'):
                    ml.package_level_id.package_id = updates.get('result_package_id')
                else:
                    # TODO: make package levels less of a pain and fix this
                    package_level = ml.package_level_id
                    ml.package_level_id = False
                    # Only need to unlink the package level if it's empty. Otherwise will unlink it to still valid move lines.
                    if not package_level.move_line_ids:
                        package_level.unlink()

        # When we try to write on a reserved move line any fields from `triggers` or directly
        # `reserved_uom_qty` (the actual reserved quantity), we need to make sure the associated
        # quants are correctly updated in order to not make them out of sync (i.e. the sum of the
        # move lines `reserved_uom_qty` should always be equal to the sum of `reserved_quantity` on
        # the quants). If the new charateristics are not available on the quants, we chose to
        # reserve the maximum possible.
        if updates or 'reserved_uom_qty' in vals:
            for ml in self.filtered(lambda ml: ml.state in ['partially_available', 'assigned'] and ml.product_id.type == 'product'):

                if 'reserved_uom_qty' in vals:
                    new_reserved_uom_qty = ml.product_uom_id._compute_quantity(
                        vals['reserved_uom_qty'], ml.product_id.uom_id, rounding_method='HALF-UP')
                    # Make sure `reserved_uom_qty` is not negative.
                    if float_compare(new_reserved_uom_qty, 0, precision_rounding=ml.product_id.uom_id.rounding) < 0:
                        raise UserError(_('Reserving a negative quantity is not allowed.'))
                else:
                    new_reserved_uom_qty = ml.reserved_qty

                # Unreserve the old charateristics of the move line.
                if not ml.move_id._should_bypass_reservation(ml.location_id):
                    Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.reserved_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

                # Reserve the maximum available of the new charateristics of the move line.
                if not ml.move_id._should_bypass_reservation(updates.get('location_id', ml.location_id)):
                    reserved_qty = 0
                    try:
                        q = Quant._update_reserved_quantity(ml.product_id, updates.get('location_id', ml.location_id), new_reserved_uom_qty, lot_id=updates.get('lot_id', ml.lot_id),
                                                             package_id=updates.get('package_id', ml.package_id), owner_id=updates.get('owner_id', ml.owner_id), strict=True)
                        reserved_qty = sum([x[1] for x in q])
                    except UserError:
                        pass
                    if reserved_qty != new_reserved_uom_qty:
                        new_reserved_uom_qty = ml.product_id.uom_id._compute_quantity(reserved_qty, ml.product_uom_id, rounding_method='HALF-UP')
                        moves_to_recompute_state |= ml.move_id
                        ml.with_context(bypass_reservation_update=True).reserved_uom_qty = new_reserved_uom_qty
                        # we don't want to override the new reserved quantity
                        vals.pop('reserved_uom_qty', None)

        # When editing a done move line, the reserved availability of a potential chained move is impacted. Take care of running again `_action_assign` on the concerned moves.
        if updates or 'qty_done' in vals:
            next_moves = self.env['stock.move']
            mls = self.filtered(lambda ml: ml.move_id.state == 'done' and ml.product_id.type == 'product')
            if not updates:  # we can skip those where qty_done is already good up to UoM rounding
                mls = mls.filtered(lambda ml: not float_is_zero(ml.qty_done - vals['qty_done'], precision_rounding=ml.product_uom_id.rounding))
            for ml in mls:
                # undo the original move line
                qty_done_orig = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
                in_date = Quant._update_available_quantity(ml.product_id, ml.location_dest_id, -qty_done_orig, lot_id=ml.lot_id,
                                                      package_id=ml.result_package_id, owner_id=ml.owner_id)[1]
                Quant._update_available_quantity(ml.product_id, ml.location_id, qty_done_orig, lot_id=ml.lot_id,
                                                      package_id=ml.package_id, owner_id=ml.owner_id, in_date=in_date)

                # move what's been actually done
                product_id = ml.product_id
                location_id = updates.get('location_id', ml.location_id)
                location_dest_id = updates.get('location_dest_id', ml.location_dest_id)
                qty_done = vals.get('qty_done', ml.qty_done)
                lot_id = updates.get('lot_id', ml.lot_id)
                package_id = updates.get('package_id', ml.package_id)
                result_package_id = updates.get('result_package_id', ml.result_package_id)
                owner_id = updates.get('owner_id', ml.owner_id)
                product_uom_id = updates.get('product_uom_id', ml.product_uom_id)
                quantity = product_uom_id._compute_quantity(qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
                if not ml.move_id._should_bypass_reservation(location_id):
                    ml._free_reservation(product_id, location_id, quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
                if not float_is_zero(quantity, precision_digits=precision):
                    available_qty, in_date = Quant._update_available_quantity(product_id, location_id, -quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
                    if available_qty < 0 and lot_id:
                        # see if we can compensate the negative quants with some untracked quants
                        untracked_qty = Quant._get_available_quantity(product_id, location_id, lot_id=False, package_id=package_id, owner_id=owner_id, strict=True)
                        if untracked_qty:
                            taken_from_untracked_qty = min(untracked_qty, abs(available_qty))
                            Quant._update_available_quantity(product_id, location_id, -taken_from_untracked_qty, lot_id=False, package_id=package_id, owner_id=owner_id)
                            Quant._update_available_quantity(product_id, location_id, taken_from_untracked_qty, lot_id=lot_id, package_id=package_id, owner_id=owner_id)
                            if not ml.move_id._should_bypass_reservation(location_id):
                                ml._free_reservation(ml.product_id, location_id, untracked_qty, lot_id=False, package_id=package_id, owner_id=owner_id)
                    Quant._update_available_quantity(product_id, location_dest_id, quantity, lot_id=lot_id, package_id=result_package_id, owner_id=owner_id, in_date=in_date)

                # Unreserve and reserve following move in order to have the real reserved quantity on move_line.
                next_moves |= ml.move_id.move_dest_ids.filtered(lambda move: move.state not in ('done', 'cancel'))

                # Log a note
                if ml.picking_id:
                    ml._log_message(ml.picking_id, ml, 'stock.track_move_template', vals)

        res = super(StockMoveLine, self).write(vals)

        # As stock_account values according to a move's `product_uom_qty`, we consider that any
        # done stock move should have its `quantity_done` equals to its `product_uom_qty`, and
        # this is what move's `action_done` will do. So, we replicate the behavior here.
        if updates or 'qty_done' in vals:
            moves = self.filtered(lambda ml: ml.move_id.state == 'done').mapped('move_id')
            moves |= self.filtered(lambda ml: not ml.move_id.origin_returned_move_id and ml.move_id.state not in ('done', 'cancel')\
                and ml.move_id.picking_id.immediate_transfer).mapped('move_id')
            for move in moves:
                move.product_uom_qty = move.quantity_done
            next_moves._do_unreserve()
            next_moves._action_assign()

        if moves_to_recompute_state:
            moves_to_recompute_state._recompute_state()

        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        for ml in self:
            if ml.state in ('done', 'cancel'):
                raise UserError(_('You can not delete product moves if the picking is done. You can only correct the done quantities.'))

    def unlink(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for ml in self:
            # Unlinking a move line should unreserve.
            if not float_is_zero(ml.reserved_qty, precision_digits=precision) and ml.move_id and not ml.move_id._should_bypass_reservation(ml.location_id):
                self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.reserved_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
        moves = self.mapped('move_id')
        package_levels = self.package_level_id
        res = super(StockMoveLine, self).unlink()
        package_levels = package_levels.filtered(lambda pl: not (pl.move_line_ids or pl.move_ids))
        if package_levels:
            package_levels.unlink()
        if moves:
            # Add with_prefetch() to set the _prefecht_ids = _ids
            # because _prefecht_ids generator look lazily on the cache of move_id
            # which is clear by the unlink of move line
            moves.with_prefetch()._recompute_state()
        return res

    def _action_done(self):
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
        ml_ids_tracked_without_lot = OrderedSet()
        ml_ids_to_delete = OrderedSet()
        ml_ids_to_create_lot = OrderedSet()
        ml_ids_to_check = defaultdict(OrderedSet)

        for ml in self:
            # Check here if `ml.qty_done` respects the rounding of `ml.product_uom_id`.
            uom_qty = float_round(ml.qty_done, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            qty_done = float_round(ml.qty_done, precision_digits=precision_digits, rounding_method='HALF-UP')
            if float_compare(uom_qty, qty_done, precision_digits=precision_digits) != 0:
                raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision '
                                  'defined on the unit of measure "%s". Please change the quantity done or the '
                                  'rounding precision of your unit of measure.') % (ml.product_id.display_name, ml.product_uom_id.name))

            qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking == 'none':
                    continue
                picking_type_id = ml.move_id.picking_type_id
                if not picking_type_id and not ml.is_inventory and not ml.lot_id:
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

        for (product, company), mls in ml_ids_to_check.items():
            mls = self.env['stock.move.line'].browse(mls)
            lots = self.env['stock.lot'].search([
                ('company_id', '=', company.id),
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
            raise UserError(_('You need to supply a Lot/Serial Number for product: \n - ') +
                              '\n - '.join(mls_tracked_without_lot.mapped('product_id.display_name')))
        ml_to_create_lot = self.env['stock.move.line'].browse(ml_ids_to_create_lot)
        if ml_ids_to_create_lot:
            ml_to_create_lot.with_context(bypass_reservation_update=True)._create_and_assign_production_lot()

        mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
        mls_to_delete.unlink()

        mls_todo = (self - mls_to_delete)
        mls_todo._check_company()

        # Now, we can actually move the quant.
        ml_ids_to_ignore = OrderedSet()

        quants_cache = self.env['stock.quant']._get_quants_by_products_locations(mls_todo.product_id, mls_todo.location_id | mls_todo.location_dest_id, extra_domain=['|', ('lot_id', 'in', mls_todo.lot_id.ids), ('lot_id', '=', False)])
        Quant = self.env['stock.quant'].with_context(quants_cache=quants_cache)

        for ml in mls_todo:
            if ml.product_id.type == 'product':
                rounding = ml.product_uom_id.rounding

                # if this move line is force assigned, unreserve elsewhere if needed
                if not ml.move_id._should_bypass_reservation(ml.location_id) and float_compare(ml.qty_done, ml.reserved_uom_qty, precision_rounding=rounding) > 0:
                    qty_done_product_uom = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id, rounding_method='HALF-UP')
                    extra_qty = qty_done_product_uom - ml.reserved_qty
                    ml._free_reservation(ml.product_id, ml.location_id, extra_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
                # unreserve what's been reserved
                if not ml.move_id._should_bypass_reservation(ml.location_id) and ml.product_id.type == 'product' and ml.reserved_qty:
                    Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.reserved_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

                # move what's been actually done
                quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
                available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                if available_qty < 0 and ml.lot_id:
                    # see if we can compensate the negative quants with some untracked quants
                    untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                    if untracked_qty:
                        taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                        Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id)
                        Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date)
            ml_ids_to_ignore.add(ml.id)
        # Reset the reserved quantity as we just moved it to the destination location.
        mls_todo.with_context(bypass_reservation_update=True).write({
            'reserved_uom_qty': 0.00,
            'date': fields.Datetime.now(),
        })

    def _get_similar_move_lines(self):
        self.ensure_one()
        lines = self.env['stock.move.line']
        picking_id = self.move_id.picking_id if self.move_id else self.picking_id
        if picking_id:
            lines |= picking_id.move_line_ids.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        return lines

    def _get_value_production_lot(self):
        self.ensure_one()
        return {
            'company_id': self.company_id.id,
            'name': self.lot_name,
            'product_id': self.product_id.id
        }

    def _create_and_assign_production_lot(self):
        """ Creates and assign new production lots for move lines."""
        lot_vals = []
        # It is possible to have multiple time the same lot to create & assign,
        # so we handle the case with 2 dictionaries.
        key_to_index = {}  # key to index of the lot
        key_to_mls = defaultdict(lambda: self.env['stock.move.line'])  # key to all mls
        for ml in self:
            key = (ml.company_id.id, ml.product_id.id, ml.lot_name)
            key_to_mls[key] |= ml
            if ml.tracking != 'lot' or key not in key_to_index:
                key_to_index[key] = len(lot_vals)
                lot_vals.append(ml._get_value_production_lot())
        lots = self.env['stock.lot'].create(lot_vals)
        for key, mls in key_to_mls.items():
            lot = lots[key_to_index[key]].with_prefetch(lots._ids)   # With prefetch to reconstruct the ones broke by accessing by index
            mls.write({'lot_id': lot.id})

    def _reservation_is_updatable(self, quantity, reserved_quant):
        self.ensure_one()
        if (self.product_id.tracking != 'serial' and
                self.location_id.id == reserved_quant.location_id.id and
                self.lot_id.id == reserved_quant.lot_id.id and
                self.package_id.id == reserved_quant.package_id.id and
                self.owner_id.id == reserved_quant.owner_id.id):
            return True
        return False

    def _log_message(self, record, move, template, vals):
        data = vals.copy()
        if 'lot_id' in vals and vals['lot_id'] != move.lot_id.id:
            data['lot_name'] = self.env['stock.lot'].browse(vals.get('lot_id')).name
        if 'location_id' in vals:
            data['location_name'] = self.env['stock.location'].browse(vals.get('location_id')).name
        if 'location_dest_id' in vals:
            data['location_dest_name'] = self.env['stock.location'].browse(vals.get('location_dest_id')).name
        if 'package_id' in vals and vals['package_id'] != move.package_id.id:
            data['package_name'] = self.env['stock.quant.package'].browse(vals.get('package_id')).name
        if 'package_result_id' in vals and vals['package_result_id'] != move.package_result_id.id:
            data['result_package_name'] = self.env['stock.quant.package'].browse(vals.get('result_package_id')).name
        if 'owner_id' in vals and vals['owner_id'] != move.owner_id.id:
            data['owner_name'] = self.env['res.partner'].browse(vals.get('owner_id')).name
        record.message_post_with_view(template, values={'move': move, 'vals': dict(vals, **data)}, subtype_id=self.env.ref('mail.mt_note').id)

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

        # Check the available quantity, with the `strict` kw set to `True`. If the available
        # quantity is greather than the quantity now unavailable, there is nothing to do.
        available_quantity = self.env['stock.quant']._get_available_quantity(
            product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True
        )
        if quantity > available_quantity:
            quantity = quantity - available_quantity
            # We now have to find the move lines that reserved our now unavailable quantity. We
            # take care to exclude ourselves and the move lines were work had already been done.
            outdated_move_lines_domain = [
                ('state', 'not in', ['done', 'cancel']),
                ('product_id', '=', product_id.id),
                ('lot_id', '=', lot_id.id if lot_id else False),
                ('location_id', '=', location_id.id),
                ('owner_id', '=', owner_id.id if owner_id else False),
                ('package_id', '=', package_id.id if package_id else False),
                ('reserved_qty', '>', 0.0),
                ('id', 'not in', tuple(ml_ids_to_ignore)),
            ]

            # We take the current picking first, then the pickings with the latest scheduled date
            current_picking_first = lambda cand: (
                cand.picking_id != self.move_id.picking_id,
                -(cand.picking_id.scheduled_date or cand.move_id.date).timestamp()
                if cand.picking_id or cand.move_id
                else -cand.id,
            )
            outdated_candidates = self.env['stock.move.line'].search(outdated_move_lines_domain).sorted(current_picking_first)

            # As the move's state is not computed over the move lines, we'll have to manually
            # recompute the moves which we adapted their lines.
            move_to_recompute_state = self.env['stock.move']
            to_unlink_candidate_ids = set()

            rounding = self.product_uom_id.rounding
            for candidate in outdated_candidates:
                if float_compare(candidate.reserved_qty, quantity, precision_rounding=rounding) <= 0:
                    quantity -= candidate.reserved_qty
                    if candidate.qty_done:
                        move_to_recompute_state |= candidate.move_id
                        candidate.reserved_uom_qty = 0.0
                    else:
                        to_unlink_candidate_ids.add(candidate.id)
                    if float_is_zero(quantity, precision_rounding=rounding):
                        break
                else:
                    # split this move line and assign the new part to our extra move
                    quantity_split = float_round(
                        candidate.reserved_qty - quantity,
                        precision_rounding=self.product_uom_id.rounding,
                        rounding_method='UP')
                    candidate.reserved_uom_qty = self.product_id.uom_id._compute_quantity(quantity_split, candidate.product_uom_id, rounding_method='HALF-UP')
                    move_to_recompute_state |= candidate.move_id
                    break
            move_line_to_unlink = self.env['stock.move.line'].browse(to_unlink_candidate_ids)
            if self.env['ir.config_parameter'].sudo().get_param('stock.break_mto'):
                for m in (move_line_to_unlink.move_id | move_to_recompute_state):
                    m.write({
                        'procure_method': 'make_to_stock',
                        'move_orig_ids': [Command.clear()]
                    })
            move_line_to_unlink.unlink()
            move_to_recompute_state._recompute_state()

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, qty_done, product_uom}, ...}
        """
        aggregated_move_lines = {}

        def get_aggregated_properties(move_line=False, move=False):
            move = move or move_line.move_id
            uom = move.product_uom or move_line.product_uom_id
            name = move.product_id.display_name
            description = move.description_picking
            if description == name or description == move.product_id.name:
                description = False
            product = move.product_id
            line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}'
            return (line_key, name, description, uom)

        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids

        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            line_key, name, description, uom = get_aggregated_properties(move_line=move_line)

            qty_done = move_line.product_uom_id._compute_quantity(move_line.qty_done, uom)
            if line_key not in aggregated_move_lines:
                qty_ordered = None
                if backorders and not kwargs.get('strict'):
                    qty_ordered = move_line.move_id.product_uom_qty
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                    # Remove the done quantities of the other move lines of the stock move
                    previous_move_lines = move_line.move_id.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key and ml.id != move_line.id
                    )
                    qty_ordered -= sum(map(lambda m: m.product_uom_id._compute_quantity(m.qty_done, uom), previous_move_lines))
                aggregated_move_lines[line_key] = {'name': name,
                                                   'description': description,
                                                   'qty_done': qty_done,
                                                   'qty_ordered': qty_ordered or qty_done,
                                                   'product_uom': uom,
                                                   'product': move_line.product_id}
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += qty_done
                aggregated_move_lines[line_key]['qty_done'] += qty_done

        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        if kwargs.get('strict'):
            return aggregated_move_lines
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_ids:
            if not (empty_move.state == "cancel" and empty_move.product_uom_qty
                    and float_is_zero(empty_move.quantity_done, precision_rounding=empty_move.product_uom.rounding)):
                continue
            line_key, name, description, uom = get_aggregated_properties(move=empty_move)

            if line_key not in aggregated_move_lines:
                qty_ordered = empty_move.product_uom_qty
                aggregated_move_lines[line_key] = {
                    'name': name,
                    'description': description,
                    'qty_done': False,
                    'qty_ordered': qty_ordered,
                    'product_uom': uom,
                    'product': empty_move.product_id,
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty

        return aggregated_move_lines

    def _compute_sale_price(self):
        # To Override
        pass

    @api.model
    def _prepare_stock_move_vals(self):
        self.ensure_one()
        return {
            'name': _('New Move:') + self.product_id.display_name,
            'product_id': self.product_id.id,
            'product_uom_qty': 0 if self.picking_id and self.picking_id.state != 'done' else self.qty_done,
            'product_uom': self.product_uom_id.id,
            'description_picking': self.description_picking,
            'location_id': self.picking_id.location_id.id,
            'location_dest_id': self.picking_id.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'state': self.picking_id.state,
            'picking_type_id': self.picking_id.picking_type_id.id,
            'restrict_partner_id': self.picking_id.owner_id.id,
            'company_id': self.picking_id.company_id.id,
            'partner_id': self.picking_id.partner_id.id,
        }

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

    def _get_revert_inventory_move_values(self):
        self.ensure_one()
        return {
            'name':_('%s [reverted]', self.reference),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.qty_done,
            'company_id': self.company_id.id or self.env.company.id,
            'state': 'confirmed',
            'location_id': self.location_dest_id.id,
            'location_dest_id': self.location_id.id,
            'is_inventory': True,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'qty_done': self.qty_done,
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
            if move_line.is_inventory and not float_is_zero(move_line.qty_done, precision_digits=move_line.product_uom_id.rounding):
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
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("The inventory adjustments have been reverted."),
            }
        }
