# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import api, Command, fields, models
from odoo.osv import expression
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order', check_company=True)
    production_id = fields.Many2one('mrp.production', 'Production Order', check_company=True)
    description_bom_line = fields.Char(related='move_id.description_bom_line')

    @api.depends('production_id')
    def _compute_picking_type_id(self):
        line_to_remove = self.env['stock.move.line']
        for line in self:
            if not line.production_id:
                continue
            line.picking_type_id = line.production_id.picking_type_id
            line_to_remove |= line
        return super(StockMoveLine, self - line_to_remove)._compute_picking_type_id()

    def _search_picking_type_id(self, operator, value):
        res = super()._search_picking_type_id(operator=operator, value=value)
        if operator in ['not in', '!=', 'not ilike']:
            if value is False:
                return expression.OR([[('production_id.picking_type_id', operator, value)], res])
            else:
                return expression.AND([[('production_id.picking_type_id', operator, value)], res])
        else:
            if value is False:
                return expression.AND([[('production_id.picking_type_id', operator, value)], res])
            else:
                return expression.OR([[('production_id.picking_type_id', operator, value)], res])

    @api.model_create_multi
    def create(self, values):
        res = super(StockMoveLine, self).create(values)
        for line in res:
            # If the line is added in a done production, we need to map it
            # manually to the produced move lines in order to see them in the
            # traceability report
            if line.move_id.raw_material_production_id and line.state == 'done':
                mo = line.move_id.raw_material_production_id
                finished_lots = mo.lot_producing_id
                finished_lots |= mo.move_finished_ids.filtered(lambda m: m.product_id != mo.product_id).move_line_ids.lot_id
                if finished_lots:
                    produced_move_lines = mo.move_finished_ids.move_line_ids.filtered(lambda sml: sml.lot_id in finished_lots)
                    line.produce_line_ids = [(6, 0, produced_move_lines.ids)]
                else:
                    produced_move_lines = mo.move_finished_ids.move_line_ids
                    line.produce_line_ids = [(6, 0, produced_move_lines.ids)]
        return res

    def _get_similar_move_lines(self):
        lines = super(StockMoveLine, self)._get_similar_move_lines()
        if self.move_id.production_id:
            finished_moves = self.move_id.production_id.move_finished_ids
            finished_move_lines = finished_moves.mapped('move_line_ids')
            lines |= finished_move_lines.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        if self.move_id.raw_material_production_id:
            raw_moves = self.move_id.raw_material_production_id.move_raw_ids
            raw_moves_lines = raw_moves.mapped('move_line_ids')
            lines |= raw_moves_lines.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        return lines

    def _reservation_is_updatable(self, quantity, reserved_quant):
        self.ensure_one()
        if self.produce_line_ids.lot_id:
            ml_remaining_qty = self.qty_done - self.reserved_uom_qty
            ml_remaining_qty = self.product_uom_id._compute_quantity(ml_remaining_qty, self.product_id.uom_id, rounding_method="HALF-UP")
            if float_compare(ml_remaining_qty, quantity, precision_rounding=self.product_id.uom_id.rounding) < 0:
                return False
        return super(StockMoveLine, self)._reservation_is_updatable(quantity, reserved_quant)

    def write(self, vals):
        for move_line in self:
            production = move_line.move_id.production_id or move_line.move_id.raw_material_production_id
            if production and move_line.state == 'done' and any(field in vals for field in ('lot_id', 'location_id', 'qty_done')):
                move_line._log_message(production, move_line, 'mrp.track_production_move_template', vals)
        return super(StockMoveLine, self).write(vals)

    def _get_aggregated_product_quantities(self, **kwargs):
        """Returns dictionary of products and corresponding values of interest grouped by optional kit_name

        Removes descriptions where description == kit_name. kit_name is expected to be passed as a
        kwargs value because this is not directly stored in move_line_ids. Unfortunately because we
        are working with aggregated data, we have to loop through the aggregation to do this removal.

        arguments: kit_name (optional): string value of a kit name passed as a kwarg
        returns: dictionary {same_key_as_super: {same_values_as_super, ...}
        """
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        kit_name = kwargs.get('kit_name')
        if kit_name:
            for aggregated_move_line in aggregated_move_lines:
                if aggregated_move_lines[aggregated_move_line]['description'] == kit_name:
                    aggregated_move_lines[aggregated_move_line]['description'] = ""
        return aggregated_move_lines


class StockMove(models.Model):
    _inherit = 'stock.move'

    created_production_id = fields.Many2one('mrp.production', 'Created Production Order', check_company=True)
    production_id = fields.Many2one(
        'mrp.production', 'Production Order for finished products', check_company=True, index='btree_not_null')
    raw_material_production_id = fields.Many2one(
        'mrp.production', 'Production Order for components', check_company=True, index='btree_not_null')
    unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Disassembly Order', check_company=True)
    consume_unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Consumed Disassembly Order', check_company=True)
    allowed_operation_ids = fields.One2many(
        'mrp.routing.workcenter', related='raw_material_production_id.bom_id.operation_ids')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation To Consume', check_company=True,
        domain="[('id', 'in', allowed_operation_ids)]")
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order To Consume', copy=False, check_company=True)
    # Quantities to process, in normalized UoMs
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line', check_company=True)
    byproduct_id = fields.Many2one(
        'mrp.bom.byproduct', 'By-products', check_company=True,
        help="By-product line that generated the move in a manufacturing order")
    unit_factor = fields.Float('Unit Factor', compute='_compute_unit_factor', store=True)
    is_done = fields.Boolean(
        'Done', compute='_compute_is_done', store=True)
    order_finished_lot_id = fields.Many2one('stock.lot', string="Finished Lot/Serial Number", related="raw_material_production_id.lot_producing_id", store=True)
    should_consume_qty = fields.Float('Quantity To Consume', compute='_compute_should_consume_qty', digits='Product Unit of Measure')
    cost_share = fields.Float(
        "Cost Share (%)", digits=(5, 2),  # decimal = 2 is important for rounding calculations!!
        help="The percentage of the final production cost for this by-product. The total of all by-products' cost share must be smaller or equal to 100.")
    product_qty_available = fields.Float('Product On Hand Quantity', related='product_id.qty_available')
    product_virtual_available = fields.Float('Product Forecasted Quantity', related='product_id.virtual_available')
    description_bom_line = fields.Char('Kit', compute='_compute_description_bom_line')
    manual_consumption = fields.Boolean(
        'Manual Consumption', compute='_compute_manual_consumption', store=True,
        help="When activated, then the registration of consumption for that component is recorded manually exclusively.\n"
             "If not activated, and any of the components consumption is edited manually on the manufacturing order, Odoo assumes manual consumption also.")

    @api.depends('state', 'product_id', 'operation_id')
    def _compute_manual_consumption(self):
        for move in self:
            if move.state != 'draft':
                continue
            move.manual_consumption = not move.raw_material_production_id.use_auto_consume_components_lots and (move.bom_line_id.manual_consumption or move.has_tracking != 'none')

    @api.depends('bom_line_id')
    def _compute_description_bom_line(self):
        bom_line_description = {}
        for bom in self.bom_line_id.bom_id:
            if bom.type != 'phantom':
                continue
            line_ids = bom.bom_line_ids.ids
            total = len(line_ids)
            name = bom.display_name
            for i, line_id in enumerate(line_ids):
                bom_line_description[line_id] = '%s - %d/%d' % (name, i+1, total)

        for move in self:
            move.description_bom_line = bom_line_description.get(move.bom_line_id.id)

    @api.depends('raw_material_production_id.priority')
    def _compute_priority(self):
        super()._compute_priority()
        for move in self:
            move.priority = move.raw_material_production_id.priority or move.priority or '0'

    @api.depends('raw_material_production_id.picking_type_id', 'production_id.picking_type_id')
    def _compute_picking_type_id(self):
        super()._compute_picking_type_id()
        for move in self:
            if move.raw_material_production_id or move.production_id:
                move.picking_type_id = (move.raw_material_production_id or move.production_id).picking_type_id

    @api.depends('raw_material_production_id.is_locked', 'production_id.is_locked')
    def _compute_is_locked(self):
        super(StockMove, self)._compute_is_locked()
        for move in self:
            if move.raw_material_production_id:
                move.is_locked = move.raw_material_production_id.is_locked
            if move.production_id:
                move.is_locked = move.production_id.is_locked

    @api.depends('state')
    def _compute_is_done(self):
        for move in self:
            move.is_done = (move.state in ('done', 'cancel'))

    @api.depends('product_uom_qty',
        'raw_material_production_id', 'raw_material_production_id.product_qty', 'raw_material_production_id.qty_produced',
        'production_id', 'production_id.product_qty', 'production_id.qty_produced')
    def _compute_unit_factor(self):
        for move in self:
            mo = move.raw_material_production_id or move.production_id
            if mo:
                move.unit_factor = move.product_uom_qty / ((mo.product_qty - mo.qty_produced) or 1)
            else:
                move.unit_factor = 1.0

    @api.depends('raw_material_production_id', 'raw_material_production_id.name', 'production_id', 'production_id.name')
    def _compute_reference(self):
        moves_with_reference = self.env['stock.move']
        for move in self:
            if move.raw_material_production_id and move.raw_material_production_id.name:
                move.reference = move.raw_material_production_id.name
                moves_with_reference |= move
            if move.production_id and move.production_id.name:
                move.reference = move.production_id.name
                moves_with_reference |= move
        super(StockMove, self - moves_with_reference)._compute_reference()

    @api.depends('raw_material_production_id.qty_producing', 'product_uom_qty', 'product_uom')
    def _compute_should_consume_qty(self):
        for move in self:
            mo = move.raw_material_production_id
            if not mo or not move.product_uom:
                move.should_consume_qty = 0
                continue
            move.should_consume_qty = float_round((mo.qty_producing - mo.qty_produced) * move.unit_factor, precision_rounding=move.product_uom.rounding)

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        if self.raw_material_production_id and self.has_tracking == 'none':
            mo = self.raw_material_production_id
            self._update_quantity_done(mo)

    @api.onchange('quantity_done')
    def _onchange_quantity_done(self):
        if self.raw_material_production_id and not self.manual_consumption and \
           self.should_consume_qty != self.quantity_done:
            self.manual_consumption = True

    @api.model
    def default_get(self, fields_list):
        defaults = super(StockMove, self).default_get(fields_list)
        if self.env.context.get('default_raw_material_production_id') or self.env.context.get('default_production_id'):
            production_id = self.env['mrp.production'].browse(self.env.context.get('default_raw_material_production_id') or self.env.context.get('default_production_id'))
            if production_id.state not in ('draft', 'cancel'):
                if production_id.state != 'done':
                    defaults['state'] = 'draft'
                else:
                    defaults['state'] = 'done'
                    defaults['additional'] = True
                defaults['product_uom_qty'] = 0.0
            elif production_id.state == 'draft':
                defaults['group_id'] = production_id.procurement_group_id.id
                defaults['reference'] = production_id.name
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        """ Enforce consistent values (i.e. match _get_move_raw_values/_get_move_finished_values) for:
        - Manually added components/byproducts specifically values we can't set via view with "default_"
        - Moves from a copied MO
        - Backorders
        """
        if self.env.context.get('force_manual_consumption'):
            for vals in vals_list:
                vals['manual_consumption'] = True
        mo_id_to_mo = defaultdict(lambda: self.env['mrp.production'])
        product_id_to_product = defaultdict(lambda: self.env['product.product'])
        for values in vals_list:
            mo_id = values.get('raw_material_production_id', False) or values.get('production_id', False)
            location_dest = self.env['stock.location'].browse(values.get('location_dest_id'))
            if mo_id and not values.get('scrapped') and not location_dest.scrap_location:
                mo = mo_id_to_mo[mo_id]
                if not mo:
                    mo = mo.browse(mo_id)
                    mo_id_to_mo[mo_id] = mo
                values['name'] = mo.name
                values['origin'] = mo._get_origin()
                values['group_id'] = mo.procurement_group_id.id
                values['propagate_cancel'] = mo.propagate_cancel
                if values.get('raw_material_production_id', False):
                    product = product_id_to_product[values['product_id']]
                    if not product:
                        product = product.browse(values['product_id'])
                    product_id_to_product[values['product_id']] = product
                    values['location_dest_id'] = mo.production_location_id.id
                    values['price_unit'] = product.standard_price
                    continue
                # produced products + byproducts
                values['location_id'] = mo.production_location_id.id
                values['date'] = mo._get_date_planned_finished()
                values['date_deadline'] = mo.date_deadline
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get('force_manual_consumption'):
            vals['manual_consumption'] = True
        if 'product_uom_qty' in vals and 'move_line_ids' in vals:
            # first update lines then product_uom_qty as the later will unreserve
            # so possibly unlink lines
            move_line_vals = vals.pop('move_line_ids')
            super().write({'move_line_ids': move_line_vals})
        return super().write(vals)

    def _action_assign(self, force_qty=False):
        res = super(StockMove, self)._action_assign(force_qty=force_qty)
        for move in self.filtered(lambda x: x.production_id or x.raw_material_production_id):
            if move.move_line_ids:
                move.move_line_ids.write({'production_id': move.raw_material_production_id.id,
                                               'workorder_id': move.workorder_id.id,})
        return res

    def _action_confirm(self, merge=True, merge_into=False):
        moves = self.action_explode()
        # we go further with the list of ids potentially changed by action_explode
        return super(StockMove, moves)._action_confirm(merge=merge, merge_into=merge_into)

    def action_explode(self):
        """ Explodes pickings """
        # in order to explode a move, we must have a picking_type_id on that move because otherwise the move
        # won't be assigned to a picking and it would be weird to explode a move into several if they aren't
        # all grouped in the same picking.
        moves_ids_to_return = OrderedSet()
        moves_ids_to_unlink = OrderedSet()
        phantom_moves_vals_list = []
        for move in self:
            if not move.picking_type_id or (move.production_id and move.production_id.product_id == move.product_id):
                moves_ids_to_return.add(move.id)
                continue
            bom = self.env['mrp.bom'].sudo()._bom_find(move.product_id, company_id=move.company_id.id, bom_type='phantom')[move.product_id]
            if not bom:
                moves_ids_to_return.add(move.id)
                continue
            if move.picking_id.immediate_transfer:
                factor = move.product_uom._compute_quantity(move.quantity_done, bom.product_uom_id) / bom.product_qty
            else:
                factor = move.product_uom._compute_quantity(move.product_uom_qty, bom.product_uom_id) / bom.product_qty
            boms, lines = bom.sudo().explode(move.product_id, factor, picking_type=bom.picking_type_id)
            for bom_line, line_data in lines:
                if move.picking_id.immediate_transfer:
                    phantom_moves_vals_list += move._generate_move_phantom(bom_line, 0, line_data['qty'])
                else:
                    phantom_moves_vals_list += move._generate_move_phantom(bom_line, line_data['qty'], 0)
            # delete the move with original product which is not relevant anymore
            moves_ids_to_unlink.add(move.id)

        self.env['stock.move'].browse(moves_ids_to_unlink).sudo().unlink()
        if phantom_moves_vals_list:
            phantom_moves = self.env['stock.move'].create(phantom_moves_vals_list)
            phantom_moves._adjust_procure_method()
            moves_ids_to_return |= phantom_moves.action_explode().ids
        return self.env['stock.move'].browse(moves_ids_to_return)

    def action_show_details(self):
        self.ensure_one()
        action = super().action_show_details()
        if self.raw_material_production_id:
            action['views'] = [(self.env.ref('mrp.view_stock_move_operations_raw').id, 'form')]
            action['context']['show_destination_location'] = False
            action['context']['force_manual_consumption'] = True
            action['context']['active_mo_id'] = self.raw_material_production_id.id
        elif self.production_id:
            action['views'] = [(self.env.ref('mrp.view_stock_move_operations_finished').id, 'form')]
            action['context']['show_source_location'] = False
            action['context']['show_reserved_quantity'] = False
        return action

    def _action_cancel(self):
        res = super(StockMove, self)._action_cancel()
        mo_to_cancel = self.mapped('raw_material_production_id').filtered(lambda p: all(m.state == 'cancel' for m in p.move_raw_ids))
        if mo_to_cancel:
            mo_to_cancel._action_cancel()
        return res

    def _prepare_move_split_vals(self, qty):
        defaults = super()._prepare_move_split_vals(qty)
        defaults['workorder_id'] = False
        return defaults

    def _prepare_procurement_origin(self):
        self.ensure_one()
        if self.raw_material_production_id and self.raw_material_production_id.orderpoint_id:
            return self.origin
        return super()._prepare_procurement_origin()

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        return {
            'picking_id': self.picking_id.id if self.picking_id else False,
            'product_id': bom_line.product_id.id,
            'product_uom': bom_line.product_uom_id.id,
            'product_uom_qty': product_qty,
            'quantity_done': quantity_done,
            'state': 'draft',  # will be confirmed below
            'name': self.name,
            'bom_line_id': bom_line.id,
        }

    def _generate_move_phantom(self, bom_line, product_qty, quantity_done):
        vals = []
        if bom_line.product_id.type in ['product', 'consu']:
            vals = self.copy_data(default=self._prepare_phantom_move_values(bom_line, product_qty, quantity_done))
            if self.state == 'assigned':
                vals['state'] = 'assigned'
        return vals

    def _is_consuming(self):
        return super()._is_consuming() or self.picking_type_id.code == 'mrp_operation'

    def _get_backorder_move_vals(self):
        self.ensure_one()
        return {
            'state': 'confirmed',
            'reservation_date': self.reservation_date,
            'date_deadline': self.date_deadline,
            'manual_consumption': self.bom_line_id.manual_consumption or self.product_id.tracking != 'none',
            'move_orig_ids': [Command.link(m.id) for m in self.mapped('move_orig_ids')],
            'move_dest_ids': [Command.link(m.id) for m in self.mapped('move_dest_ids')],
            'procure_method': self.procure_method,
        }

    def _get_source_document(self):
        res = super()._get_source_document()
        return res or self.production_id or self.raw_material_production_id

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.production_id and self.production_id.state not in ('done', 'cancel'):
            return [(self.production_id, self.production_id.user_id, visited)]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)

    def _delay_alert_get_documents(self):
        res = super(StockMove, self)._delay_alert_get_documents()
        productions = self.raw_material_production_id | self.production_id
        return res + list(productions)

    def _should_be_assigned(self):
        res = super(StockMove, self)._should_be_assigned()
        return bool(res and not (self.production_id or self.raw_material_production_id))

    def _should_bypass_set_qty_producing(self):
        if self.state in ('done', 'cancel'):
            return True
        # Do not update extra product quantities
        if float_is_zero(self.product_uom_qty, precision_rounding=self.product_uom.rounding):
            return True
        if (not self.raw_material_production_id.use_auto_consume_components_lots and self.has_tracking != 'none') or self.manual_consumption or self._origin.manual_consumption:
            return True
        return False

    def _should_bypass_reservation(self, forced_location=False):
        res = super(StockMove, self)._should_bypass_reservation(
            forced_location=forced_location)
        return bool(res and not self.production_id)

    def _key_assign_picking(self):
        keys = super(StockMove, self)._key_assign_picking()
        return keys + (self.created_production_id,)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        return super()._prepare_merge_moves_distinct_fields() + ['created_production_id', 'cost_share', 'bom_line_id']

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return super()._prepare_merge_negative_moves_excluded_distinct_fields() + ['created_production_id']

    def _compute_kit_quantities(self, product_id, kit_qty, kit_bom, filters):
        """ Computes the quantity delivered or received when a kit is sold or purchased.
        A ratio 'qty_processed/qty_needed' is computed for each component, and the lowest one is kept
        to define the kit's quantity delivered or received.
        :param product_id: The kit itself a.k.a. the finished product
        :param kit_qty: The quantity from the order line
        :param kit_bom: The kit's BoM
        :param filters: Dict of lambda expression to define the moves to consider and the ones to ignore
        :return: The quantity delivered or received
        """
        qty_ratios = []
        boms, bom_sub_lines = kit_bom.explode(product_id, kit_qty)
        for bom_line, bom_line_data in bom_sub_lines:
            # skip service since we never deliver them
            if bom_line.product_id.type == 'service':
                continue
            if float_is_zero(bom_line_data['qty'], precision_rounding=bom_line.product_uom_id.rounding):
                # As BoMs allow components with 0 qty, a.k.a. optionnal components, we simply skip those
                # to avoid a division by zero.
                continue
            bom_line_moves = self.filtered(lambda m: m.bom_line_id == bom_line)
            if bom_line_moves:
                # We compute the quantities needed of each components to make one kit.
                # Then, we collect every relevant moves related to a specific component
                # to know how many are considered delivered.
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id, round=False)
                if not qty_per_kit:
                    continue
                incoming_moves = bom_line_moves.filtered(filters['incoming_moves'])
                outgoing_moves = bom_line_moves.filtered(filters['outgoing_moves'])
                qty_processed = sum(incoming_moves.mapped('product_qty')) - sum(outgoing_moves.mapped('product_qty'))
                # We compute a ratio to know how many kits we can produce with this quantity of that specific component
                qty_ratios.append(float_round(qty_processed / qty_per_kit, precision_rounding=bom_line.product_id.uom_id.rounding))
            else:
                return 0.0
        if qty_ratios:
            # Now that we have every ratio by components, we keep the lowest one to know how many kits we can produce
            # with the quantities delivered of each component. We use the floor division here because a 'partial kit'
            # doesn't make sense.
            return min(qty_ratios) // 1
        else:
            return 0.0

    def _show_details_in_draft(self):
        self.ensure_one()
        production = self.raw_material_production_id or self.production_id
        if production and (self.state != 'draft' or production.state != 'draft'):
            return True
        elif production:
            return False
        else:
            return super()._show_details_in_draft()

    def _update_quantity_done(self, mo):
        self.ensure_one()
        new_qty = float_round((mo.qty_producing - mo.qty_produced) * self.unit_factor, precision_rounding=self.product_uom.rounding)
        if not self.is_quantity_done_editable:
            self.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
            self.move_line_ids = self._set_quantity_done_prepare_vals(new_qty)
        else:
            self.quantity_done = new_qty

    def _update_candidate_moves_list(self, candidate_moves_list):
        super()._update_candidate_moves_list(candidate_moves_list)
        for production in self.mapped('raw_material_production_id'):
            candidate_moves_list.append(production.move_raw_ids)
        for production in self.mapped('production_id'):
            candidate_moves_list.append(production.move_finished_ids)

    def _multi_line_quantity_done_set(self, quantity_done):
        if self.raw_material_production_id:
            self.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
            self.move_line_ids = self._set_quantity_done_prepare_vals(quantity_done)
        else:
            super()._multi_line_quantity_done_set(quantity_done)

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        res['bom_line_id'] = self.bom_line_id.id
        return res

    def _get_mto_procurement_date(self):
        date = super()._get_mto_procurement_date()
        if 'manufacture' in self.product_id._get_rules_from_location(self.location_id).mapped('action'):
            date -= relativedelta(days=self.company_id.manufacturing_lead)
        return date

    def action_open_reference(self):
        res = super().action_open_reference()
        source = self.production_id or self.raw_material_production_id
        if source and source.check_access_rights('read', raise_exception=False):
            return {
                'res_model': source._name,
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': source.id,
            }
        return res
