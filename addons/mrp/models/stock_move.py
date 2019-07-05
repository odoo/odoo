# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    production_id = fields.Many2one('mrp.production', 'Production Order')
    lot_produced_ids = fields.Many2many('stock.production.lot', string='Finished Lot/Serial Number')
    lot_produced_qty = fields.Float(
        'Quantity Finished Product', digits='Product Unit of Measure',
        help="Informative, not used in matching")
    done_move = fields.Boolean('Move Done', related='move_id.is_done', readonly=False, store=True)  # TDE FIXME: naming

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
        if self.lot_produced_ids:
            ml_remaining_qty = self.qty_done - self.product_uom_qty
            ml_remaining_qty = self.product_uom_id._compute_quantity(ml_remaining_qty, self.product_id.uom_id, rounding_method="HALF-UP")
            if float_compare(ml_remaining_qty, quantity, precision_rounding=self.product_id.uom_id.rounding) < 0:
                return False
        return super(StockMoveLine, self)._reservation_is_updatable(quantity, reserved_quant)

    @api.multi
    def write(self, vals):
        for move_line in self:
            if move_line.move_id.production_id and 'lot_id' in vals:
                move_line.production_id.move_raw_ids.mapped('move_line_ids')\
                    .filtered(lambda r: not r.done_move and move_line.lot_id in r.lot_produced_ids)\
                    .write({'lot_produced_ids': [(4, vals['lot_id'])]})
            production = move_line.move_id.production_id or move_line.move_id.raw_material_production_id
            if production and move_line.state == 'done' and any(field in vals for field in ('lot_id', 'location_id', 'qty_done')):
                move_line._log_message(production, move_line, 'mrp.track_production_move_template', vals)
        return super(StockMoveLine, self).write(vals)


class StockMove(models.Model):
    _inherit = 'stock.move'

    created_production_id = fields.Many2one('mrp.production', 'Created Production Order')
    production_id = fields.Many2one(
        'mrp.production', 'Production Order for finished products')
    raw_material_production_id = fields.Many2one(
        'mrp.production', 'Production Order for components')
    unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Disassembly Order')
    consume_unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Consumed Disassembly Order')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation To Consume')  # TDE FIXME: naming
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order To Consume')
    # Quantities to process, in normalized UoMs
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line')
    byproduct_id = fields.Many2one(
        'mrp.bom.byproduct', 'By-products',
        help="By-product line that generated the move in a manufacturing order")
    unit_factor = fields.Float('Unit Factor', default=1)
    is_done = fields.Boolean(
        'Done', compute='_compute_is_done',
        store=True,
        help='Technical Field to order moves')
    needs_lots = fields.Boolean('Tracking', compute='_compute_needs_lots')
    order_finished_lot_ids = fields.Many2many('stock.production.lot', compute='_compute_order_finished_lot_ids')
    finished_lots_exist = fields.Boolean('Finished Lots Exist', compute='_compute_order_finished_lot_ids')

    def _unreserve_initial_demand(self, new_move):
        # If you were already putting stock.move.lots on the next one in the work order, transfer those to the new move
        self.filtered(lambda m: m.production_id or m.raw_material_production_id)\
        .mapped('move_line_ids')\
        .filtered(lambda ml: ml.qty_done == 0.0)\
        .write({'move_id': new_move, 'product_uom_qty': 0})

    @api.depends('raw_material_production_id.move_finished_ids.move_line_ids.lot_id')
    def _compute_order_finished_lot_ids(self):
        for move in self:
            if move.raw_material_production_id.move_finished_ids:
                finished_lots_ids = move.raw_material_production_id.move_finished_ids.mapped('move_line_ids.lot_id').ids
                if finished_lots_ids:
                    move.order_finished_lot_ids = finished_lots_ids
                    move.finished_lots_exist = True
                else:
                    move.finished_lots_exist = False

    @api.depends('product_id.tracking')
    def _compute_needs_lots(self):
        for move in self:
            move.needs_lots = move.product_id.tracking != 'none'

    @api.depends('raw_material_production_id.is_locked', 'picking_id.is_locked')
    def _compute_is_locked(self):
        super(StockMove, self)._compute_is_locked()
        for move in self:
            if move.raw_material_production_id:
                move.is_locked = move.raw_material_production_id.is_locked

    @api.depends('state')
    def _compute_is_done(self):
        for move in self:
            move.is_done = (move.state in ('done', 'cancel'))

    @api.model
    def default_get(self, fields_list):
        defaults = super(StockMove, self).default_get(fields_list)
        if self.env.context.get('default_raw_material_production_id'):
            production_id = self.env['mrp.production'].browse(self.env.context['default_raw_material_production_id'])
            if production_id.state == 'done':
                defaults['state'] = 'done'
                defaults['product_uom_qty'] = 0.0
                defaults['additional'] = True
        return defaults

    def _action_assign(self):
        res = super(StockMove, self)._action_assign()
        for move in self.filtered(lambda x: x.production_id or x.raw_material_production_id):
            if move.move_line_ids:
                move.move_line_ids.write({'production_id': move.raw_material_production_id.id,
                                               'workorder_id': move.workorder_id.id,})
        return res

    def _action_cancel(self):
        if any(move.quantity_done and (move.raw_material_production_id or move.production_id) for move in self):
            raise exceptions.UserError(_('You cannot cancel a manufacturing order if you have already consumed material.\
             If you want to cancel this MO, please change the consumed quantities to 0.'))
        return super(StockMove, self)._action_cancel()

    def _action_confirm(self, merge=True, merge_into=False):
        moves = self.env['stock.move']
        for move in self:
            moves |= move.action_explode()
        # we go further with the list of ids potentially changed by action_explode
        return super(StockMove, moves)._action_confirm(merge=merge, merge_into=merge_into)

    def action_explode(self):
        """ Explodes pickings """
        # in order to explode a move, we must have a picking_type_id on that move because otherwise the move
        # won't be assigned to a picking and it would be weird to explode a move into several if they aren't
        # all grouped in the same picking.
        if not self.picking_type_id:
            return self
        bom = self.env['mrp.bom'].sudo()._bom_find(product=self.product_id, company_id=self.company_id.id, bom_type='phantom')
        if not bom:
            return self
        phantom_moves = self.env['stock.move']
        processed_moves = self.env['stock.move']
        if self.picking_id.immediate_transfer:
            factor = self.product_uom._compute_quantity(self.quantity_done, bom.product_uom_id) / bom.product_qty
        else:
            factor = self.product_uom._compute_quantity(self.product_uom_qty, bom.product_uom_id) / bom.product_qty
        boms, lines = bom.sudo().explode(self.product_id, factor, picking_type=bom.picking_type_id)
        for bom_line, line_data in lines:
            if self.picking_id.immediate_transfer:
                phantom_moves += self._generate_move_phantom(bom_line, 0, line_data['qty'])
            else:
                phantom_moves += self._generate_move_phantom(bom_line, line_data['qty'], 0)

        for new_move in phantom_moves:
            processed_moves |= new_move.action_explode()
#         if not self.split_from and self.procurement_id:
#             # Check if procurements have been made to wait for
#             moves = self.procurement_id.move_ids
#             if len(moves) == 1:
#                 self.procurement_id.write({'state': 'done'})
        if processed_moves and self.state == 'assigned':
            # Set the state of resulting moves according to 'assigned' as the original move is assigned
            processed_moves.write({'state': 'assigned'})
        # delete the move with original product which is not relevant anymore
        self.sudo().unlink()
        return processed_moves

    def _decrease_reserved_quanity(self, quantity):
        """ Decrease the reservation on move lines but keeps the
        all other data.
        """
        move_line_to_unlink = self.env['stock.move.line']
        for move in self:
            reserved_quantity = quantity
            for move_line in self.move_line_ids:
                if move_line.product_uom_qty > reserved_quantity:
                    move_line.product_uom_qty = reserved_quantity
                else:
                    move_line.product_uom_qty = 0
                    reserved_quantity -= move_line.product_uom_qty
                if not move_line.product_uom_qty and not move_line.qty_done:
                    move_line_to_unlink |= move_line
        move_line_to_unlink.unlink()
        return True

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
        if bom_line.product_id.type in ['product', 'consu']:
            move = self.copy(default=self._prepare_phantom_move_values(bom_line, product_qty, quantity_done))
            move._adjust_procure_method()
            return move
        return self.env['stock.move']

    def _get_upstream_documents_and_responsibles(self, visited):
            if self.created_production_id and self.created_production_id.state not in ('done', 'cancel'):
                return [(self.created_production_id, self.created_production_id.user_id, visited)]
            else:
                return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)

    def _delay_alert_get_documents(self):
        res = super(StockMove, self)._delay_alert_get_documents()
        productions = self.mapped('raw_material_production_id')
        return res + list(productions)

    def _should_be_assigned(self):
        res = super(StockMove, self)._should_be_assigned()
        return bool(res and not (self.production_id or self.raw_material_production_id))

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
                # We compute the quantities needed of each components to make one kit.
                # Then, we collect every relevant moves related to a specific component
                # to know how many are considered delivered.
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id)
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
