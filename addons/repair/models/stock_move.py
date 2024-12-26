# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models
from odoo.tools.misc import groupby

MAP_REPAIR_LINE_TYPE_TO_MOVE_LOCATIONS_FROM_REPAIR = {
    'add': {'location_id': 'location_id', 'location_dest_id': 'location_dest_id'},
    'remove': {'location_id': 'location_dest_id', 'location_dest_id': 'parts_location_id'},
    'recycle': {'location_id': 'location_dest_id', 'location_dest_id': 'recycle_location_id'},
}


class StockMove(models.Model):
    _inherit = 'stock.move'

    repair_id = fields.Many2one('repair.order', check_company=True)
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

    @api.depends('repair_id', 'repair_id.location_dest_id')
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

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for move, vals in zip(self, vals_list):
            if 'repair_id' in default or move.repair_id:
                vals['sale_line_id'] = False
        return vals_list

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        self.filtered('repair_id')._action_cancel()
        return super()._unlink_if_draft_or_cancel()

    def unlink(self):
        self._clean_repair_sale_order_line()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('repair_id') or 'repair_line_type' not in vals:
                continue
            repair_id = self.env['repair.order'].browse([vals['repair_id']])
            vals['name'] = repair_id.name
            src_location, dest_location = self._get_repair_locations(vals['repair_line_type'], repair_id)
            if not vals.get('location_id'):
                vals['location_id'] = src_location.id
            if not vals.get('location_dest_id'):
                vals['location_dest_id'] = dest_location.id
        moves = super().create(vals_list)
        repair_moves = self.env['stock.move']
        for move in moves:
            if not move.repair_id:
                continue
            move.group_id = move.repair_id.procurement_group_id.id
            move.origin = move.name
            move.picking_type_id = move.repair_id.picking_type_id.id
            repair_moves |= move
        no_repair_moves = moves - repair_moves
        draft_repair_moves = repair_moves.filtered(lambda m: m.state == 'draft' and m.repair_id.state in ('confirmed', 'under_repair'))
        other_repair_moves = repair_moves - draft_repair_moves
        draft_repair_moves._check_company()
        draft_repair_moves._adjust_procure_method(picking_type_code='repair_operation')
        res = draft_repair_moves._action_confirm()
        res._trigger_scheduler()
        confirmed_repair_moves = (res | other_repair_moves)
        confirmed_repair_moves._create_repair_sale_order_line()
        return (confirmed_repair_moves | no_repair_moves)

    def write(self, vals):
        res = super().write(vals)
        repair_moves = self.env['stock.move']
        moves_to_create_so_line = self.env['stock.move']
        for move in self:
            if not move.repair_id:
                continue
            # checks vals update
            if 'repair_line_type' in vals or 'picking_type_id' in vals and move.repair_line_type:
                move.location_id, move.location_dest_id = move._get_repair_locations(move.repair_line_type)
            if not move.sale_line_id and 'sale_line_id' not in vals and move.repair_line_type == 'add':
                moves_to_create_so_line |= move
            if move.sale_line_id and ('repair_line_type' in vals or 'product_uom_qty' in vals):
                repair_moves |= move

        repair_moves._update_repair_sale_order_line()
        moves_to_create_so_line._create_repair_sale_order_line()
        return res

    def action_add_from_catalog_repair(self):
        repair_order = self.env['repair.order'].browse(self.env.context.get('order_id'))
        return repair_order.action_add_from_catalog()

    # Needed to also cancel the lastly added part
    def _action_cancel(self):
        self._clean_repair_sale_order_line()
        return super()._action_cancel()

    def _create_repair_sale_order_line(self):
        if not self:
            return
        so_line_vals = []
        for move in self:
            if move.sale_line_id or move.repair_line_type != 'add' or not move.repair_id.sale_order_id:
                continue
            product_qty = move.product_uom_qty if move.repair_id.state != 'done' else move.quantity
            so_line_vals.append({
                'order_id': move.repair_id.sale_order_id.id,
                'product_id': move.product_id.id,
                'product_uom_qty': product_qty, # When relying only on so_line compute method, the sol quantity is only updated on next sol creation
                'product_uom': move.product_uom.id,
                'move_ids': [Command.link(move.id)],
                'qty_delivered': move.quantity if move.state == 'done' else 0.0,
            })
            if move.repair_id.under_warranty:
                so_line_vals[-1]['price_unit'] = 0.0
            elif move.price_unit:
                so_line_vals[-1]['price_unit'] = move.price_unit

        self.env['sale.order.line'].create(so_line_vals)

    def _clean_repair_sale_order_line(self):
        self.filtered(
            lambda m: m.repair_id and m.sale_line_id
        ).mapped('sale_line_id').write({'product_uom_qty': 0.0})

    def _update_repair_sale_order_line(self):
        if not self:
            return
        moves_to_clean = self.env['stock.move']
        moves_to_update = self.env['stock.move']
        for move in self:
            if not move.repair_id:
                continue
            if move.sale_line_id and move.repair_line_type != 'add':
                moves_to_clean |= move
            if move.sale_line_id and move.repair_line_type == 'add':
                moves_to_update |= move
        moves_to_clean._clean_repair_sale_order_line()
        for sale_line, _ in groupby(moves_to_update, lambda m: m.sale_line_id):
            sale_line.product_uom_qty = sum(sale_line.move_ids.mapped('product_uom_qty'))

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
