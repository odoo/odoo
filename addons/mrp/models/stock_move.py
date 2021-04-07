# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order', check_company=True)
    production_id = fields.Many2one('mrp.production', 'Production Order', check_company=True)

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
            ml_remaining_qty = self.qty_done - self.product_uom_qty
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
        'mrp.production', 'Production Order for finished products', check_company=True, index=True)
    raw_material_production_id = fields.Many2one(
        'mrp.production', 'Production Order for components', check_company=True, index=True)
    unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Disassembly Order', check_company=True)
    consume_unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Consumed Disassembly Order', check_company=True)
    allowed_operation_ids = fields.Many2many('mrp.routing.workcenter', compute='_compute_allowed_operation_ids')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation To Consume', check_company=True,
        domain="[('id', 'in', allowed_operation_ids)]")
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order To Consume', check_company=True)
    # Quantities to process, in normalized UoMs
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line', check_company=True)
    byproduct_id = fields.Many2one(
        'mrp.bom.byproduct', 'By-products', check_company=True,
        help="By-product line that generated the move in a manufacturing order")
    unit_factor = fields.Float('Unit Factor', compute='_compute_unit_factor', store=True)
    is_done = fields.Boolean(
        'Done', compute='_compute_is_done',
        store=True,
        help='Technical Field to order moves')
    order_finished_lot_ids = fields.Many2many('stock.production.lot', string="Finished Lot/Serial Number", compute='_compute_order_finished_lot_ids')
    should_consume_qty = fields.Float('Quantity To Consume', compute='_compute_should_consume_qty', digits='Product Unit of Measure')

    @api.depends('raw_material_production_id.priority')
    def _compute_priority(self):
        super()._compute_priority()
        for move in self:
            move.priority = move.raw_material_production_id.priority or move.priority or '0'

    @api.depends('raw_material_production_id.lot_producing_id')
    def _compute_order_finished_lot_ids(self):
        for move in self:
            move.order_finished_lot_ids = move.raw_material_production_id.lot_producing_id

    @api.depends('raw_material_production_id.bom_id')
    def _compute_allowed_operation_ids(self):
        for move in self:
            if (
                not move.raw_material_production_id or
                not move.raw_material_production_id.bom_id or not
                move.raw_material_production_id.bom_id.operation_ids
            ):
                move.allowed_operation_ids = self.env['mrp.routing.workcenter']
            else:
                operation_domain = [
                    ('id', 'in', move.raw_material_production_id.bom_id.operation_ids.ids),
                    '|',
                        ('company_id', '=', self.company_id.id),
                        ('company_id', '=', False)
                ]
                move.allowed_operation_ids = self.env['mrp.routing.workcenter'].search(operation_domain)

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

    @api.depends('raw_material_production_id.qty_producing', 'product_uom_qty')
    def _compute_should_consume_qty(self):
        for move in self:
            mo = move.raw_material_production_id
            if not mo:
                move.should_consume_qty = 0
                continue
            move.should_consume_qty = mo.product_uom_id._compute_quantity((mo.qty_producing - mo.qty_produced) * move.unit_factor, mo.product_uom_id, rounding_method='HALF-UP')

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        if self.raw_material_production_id and self.has_tracking == 'none':
            mo = self.raw_material_production_id
            self._update_quantity_done(mo)

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
                defaults['product_uom_qty'] = 0.0
                defaults['additional'] = True
        return defaults

    def unlink(self):
        # Avoid deleting move related to active MO
        for move in self:
            if move.production_id and move.production_id.state not in ('draft', 'cancel'):
                raise UserError(_('Please cancel the Manufacture Order first.'))
        return super(StockMove, self).unlink()

    def _action_assign(self):
        res = super(StockMove, self)._action_assign()
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
            bom = self.env['mrp.bom'].sudo()._bom_find(product=move.product_id, company_id=move.company_id.id, bom_type='phantom')
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
        elif self.production_id:
            action['views'] = [(self.env.ref('mrp.view_stock_move_operations_finished').id, 'form')]
            action['context']['show_source_location'] = False
        return action

    def _action_cancel(self):
        res = super(StockMove, self)._action_cancel()
        for production in self.mapped('raw_material_production_id'):
            if production.state != 'cancel':
                continue
            production._action_cancel()
        return res

    def _prepare_move_split_vals(self, qty):
        defaults = super()._prepare_move_split_vals(qty)
        defaults['workorder_id'] = False
        return defaults

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

    @api.model
    def _consuming_picking_types(self):
        res = super()._consuming_picking_types()
        res.append('mrp_operation')
        return res

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
        if self.has_tracking != 'none' or self.state == 'done':
            return True
        return False

    def _should_bypass_reservation(self):
        res = super(StockMove, self)._should_bypass_reservation()
        return bool(res and not self.production_id)

    def _key_assign_picking(self):
        keys = super(StockMove, self)._key_assign_picking()
        return keys + (self.created_production_id,)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        distinct_fields.append('created_production_id')
        return distinct_fields

    @api.model
    def _prepare_merge_move_sort_method(self, move):
        keys_sorted = super()._prepare_merge_move_sort_method(move)
        keys_sorted.append(move.created_production_id.id)
        return keys_sorted

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
            bom_line_moves = self.filtered(lambda m: m.bom_line_id == bom_line)
            if bom_line_moves:
                if float_is_zero(bom_line_data['qty'], precision_rounding=bom_line.product_uom_id.rounding):
                    # As BoMs allow components with 0 qty, a.k.a. optionnal components, we simply skip those
                    # to avoid a division by zero.
                    continue
                # We compute the quantities needed of each components to make one kit.
                # Then, we collect every relevant moves related to a specific component
                # to know how many are considered delivered.
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id)
                if not qty_per_kit:
                    continue
                incoming_moves = bom_line_moves.filtered(filters['incoming_moves'])
                outgoing_moves = bom_line_moves.filtered(filters['outgoing_moves'])
                qty_processed = sum(incoming_moves.mapped('product_qty')) - sum(outgoing_moves.mapped('product_qty'))
                # We compute a ratio to know how many kits we can produce with this quantity of that specific component
                qty_ratios.append(qty_processed / qty_per_kit)
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
        new_qty = mo.product_uom_id._compute_quantity((mo.qty_producing - mo.qty_produced) * self.unit_factor, mo.product_uom_id, rounding_method='HALF-UP')
        if not self.is_quantity_done_editable:
            self.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
            self.move_line_ids = self._set_quantity_done_prepare_vals(new_qty)
        else:
            self.quantity_done = new_qty
