# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models


MAP_REPAIR_LINE_TYPE_TO_MOVE_LOCATIONS_FROM_REPAIR = {
    'add': {'location_id': 'location_id', 'location_dest_id': 'location_dest_id'},
    'remove': {'location_id': 'location_dest_id', 'location_dest_id': 'parts_location_id'},
    'recycle': {'location_id': 'location_dest_id', 'location_dest_id': 'recycle_location_id'},
}


class StockMove(models.Model):
    _inherit = 'stock.move'

    repair_id = fields.Many2one('repair.order', check_company=True, index='btree_not_null', copy=False, ondelete='cascade')
    repair_line_type = fields.Selection([
        ('add', 'Add'),
        ('remove', 'Remove'),
        ('recycle', 'Recycle')
    ], 'Type', store=True, index=True)

    @api.depends('repair_line_type')
    def _compute_forecast_information(self):
        moves_to_compute = self.filtered(lambda move: not move.repair_line_type or move.repair_line_type == 'add')
        for move in (self - moves_to_compute):
            move.forecast_availability = move.product_qty
            move.forecast_expected_date = False
        return super(StockMove, moves_to_compute)._compute_forecast_information()

    @api.depends('repair_id.picking_type_id')
    def _compute_picking_type_id(self):
        remaining_moves = self
        for move in self:
            if move.repair_id:
                move.picking_type_id = move.repair_id.picking_type_id
                remaining_moves -= move
        return super(StockMove, remaining_moves)._compute_picking_type_id()

    @api.depends('repair_id.location_id', 'repair_line_type')
    def _compute_location_id(self):
        ids_to_super = set()
        for move in self:
            if move.repair_id and move.repair_line_type:
                move.location_id = move.repair_id[
                    MAP_REPAIR_LINE_TYPE_TO_MOVE_LOCATIONS_FROM_REPAIR[move.repair_line_type]['location_id']
                ]
            else:
                ids_to_super.add(move.id)
        return super(StockMove, self.browse(ids_to_super))._compute_location_id()

    @api.depends('repair_id.location_dest_id', 'repair_line_type')
    def _compute_location_dest_id(self):
        ids_to_super = set()
        for move in self:
            if move.repair_id and move.repair_line_type:
                move.location_dest_id = move.repair_id[
                    MAP_REPAIR_LINE_TYPE_TO_MOVE_LOCATIONS_FROM_REPAIR[move.repair_line_type]['location_dest_id']
                ]
            else:
                ids_to_super.add(move.id)
        return super(StockMove, self.browse(ids_to_super))._compute_location_dest_id()

    @api.depends('repair_id.name')
    def _compute_reference(self):
        moves_with_reference = set()
        for move in self:
            if move.repair_id and move.repair_id.name:
                move.reference = move.repair_id.name
                moves_with_reference.add(move.id)
        super(StockMove, self - self.env['stock.move'].browse(moves_with_reference))._compute_reference()

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        self.filtered('repair_id')._action_cancel()
        return super()._unlink_if_draft_or_cancel()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('repair_id') or 'repair_line_type' not in vals:
                continue
            repair_id = self.env['repair.order'].browse([vals['repair_id']])
            vals['origin'] = repair_id.name
        moves = super().create(vals_list)
        repair_moves = self.env['stock.move']
        for move in moves:
            if not move.repair_id:
                continue
            move.reference_ids = [Command.link(r.id) for r in move.repair_id.reference_ids]
            move.picking_type_id = move.repair_id.picking_type_id.id
            repair_moves |= move
        no_repair_moves = moves - repair_moves
        draft_repair_moves = repair_moves.filtered(lambda m: m.state == 'draft' and m.repair_id.state == 'confirmed')
        other_repair_moves = repair_moves - draft_repair_moves
        draft_repair_moves._check_company()
        draft_repair_moves._adjust_procure_method(picking_type_code='repair_operation')
        res = draft_repair_moves._action_confirm()
        res._trigger_scheduler()
        confirmed_repair_moves = (res | other_repair_moves)
        return (confirmed_repair_moves | no_repair_moves)

    def action_add_from_catalog_repair(self):
        repair_order = self.env['repair.order'].browse(self.env.context.get('order_id'))
        return repair_order.with_context(child_field='move_ids').action_add_from_catalog()

    def _is_consuming(self):
        return super()._is_consuming() or (self.repair_id and self.repair_line_type == 'add')

    def _get_repair_locations(self, repair_line_type, repair_id=False):
        location_map = MAP_REPAIR_LINE_TYPE_TO_MOVE_LOCATIONS_FROM_REPAIR.get(repair_line_type)
        if location_map:
            if not repair_id:
                self.repair_id.ensure_one()
                repair_id = self.repair_id
            location_id, location_dest_id = [repair_id[field] for field in location_map.values()]
        else:
            location_id, location_dest_id = False, False
        return location_id, location_dest_id

    def _get_source_document(self):
        return self.repair_id or super()._get_source_document()

    def _set_repair_locations(self):
        moves_per_repair = self.filtered(lambda m: (m.repair_id and m.repair_line_type) is not False).grouped('repair_id')
        if not moves_per_repair:
            return
        for moves in moves_per_repair.values():
            grouped_moves = moves.grouped('repair_line_type')
            for line_type, m in grouped_moves.items():
                m.location_id, m.location_dest_id = m._get_repair_locations(line_type)

    def _should_be_assigned(self):
        if self.repair_id:
            return False
        return super()._should_be_assigned()

    def _split(self, qty, restrict_partner_id=False):
        # When setting the Repair Order as done with partially done moves, do not split these moves
        if self.repair_id:
            return []
        return super(StockMove, self)._split(qty, restrict_partner_id)

    def action_show_details(self):
        action = super().action_show_details()
        if self.repair_line_type == 'recycle':
            action['context'].update({'show_quant': False, 'show_destination_location': True})
        return action
