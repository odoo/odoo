# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, fields, models, _
from odoo.osv import expression
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import OrderedSet


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    batch_id = fields.Many2one(related='picking_id.batch_id', store=True)

    def action_open_add_to_wave(self):
        # This action can be called from the move line list view or from the 'Add to wave' wizard
        if 'active_wave_id' in self.env.context:
            wave = self.env['stock.picking.batch'].browse(self.env.context.get('active_wave_id'))
            return self._add_to_wave(wave)
        view = self.env.ref('stock_picking_batch.stock_add_to_wave_form')
        return {
            'name': _('Add to Wave'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.add.to.wave',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
        }

    def _add_to_wave(self, wave=False, description=False):
        """ Detach lines (and corresponding stock move from a picking to another). If wave is
        passed, attach new picking into it. If not attach line to their original picking.

        :param int wave: id of the wave picking on which to put the move lines. """

        if not wave:
            wave = self.env['stock.picking.batch'].create({
                'is_wave': True,
                'picking_type_id': self.picking_type_id and self.picking_type_id[0].id,
                'user_id': self.env.context.get('active_owner_id'),
                'description': description,
            })
        line_by_picking = defaultdict(lambda: self.env['stock.move.line'])
        for line in self:
            line_by_picking[line.picking_id] |= line
        picking_to_wave_vals_list = []
        for picking, lines in line_by_picking.items():
            # Move the entire picking if all the line are taken
            line_by_move = defaultdict(lambda: self.env['stock.move.line'])
            qty_by_move = defaultdict(float)
            for line in lines:
                move = line.move_id
                line_by_move[move] |= line
                qty = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id, rounding_method='HALF-UP')
                qty_by_move[line.move_id] += qty

            if lines == picking.move_line_ids and lines.move_id == picking.move_ids:
                move_complete = True
                for move, qty in qty_by_move.items():
                    if float_compare(move.product_qty, qty, precision_rounding=move.product_uom.rounding) != 0:
                        move_complete = False
                        break
                if move_complete:
                    wave.picking_ids = [Command.link(picking.id)]
                    continue

            # Split the picking in two part to extract only line that are taken on the wave
            picking_to_wave_vals = picking.copy_data({
                'move_ids': [],
                'move_line_ids': [],
                'batch_id': wave.id,
            })[0]
            for move, move_lines in line_by_move.items():
                picking_to_wave_vals['move_line_ids'] += [Command.link(line.id) for line in lines]
                # if all the line of a stock move are taken we change the picking on the stock move
                if move_lines == move.move_line_ids:
                    picking_to_wave_vals['move_ids'] += [Command.link(move.id)]
                    continue
                # Split the move
                qty = qty_by_move[move]
                new_move = move._split(qty)
                new_move[0]['move_line_ids'] = [Command.set(move_lines.ids)]
                picking_to_wave_vals['move_ids'] += [Command.create(new_move[0])]

            picking_to_wave_vals_list.append(picking_to_wave_vals)

        if picking_to_wave_vals_list:
            self.env['stock.picking'].create(picking_to_wave_vals_list)
        wave.action_confirm()

    def _is_auto_wave_batchable(self):
        self.ensure_one()
        return not (not self.picking_id
           or self.state != 'assigned'
           or not self.quantity
           or self.batch_id.is_wave
           or not self.picking_type_id._is_auto_wave_grouped()
           or (self.picking_type_id.wave_group_by_category and self.product_id.categ_id not in self.picking_type_id.wave_category_ids))

    def _find_auto_wave(self):
        """Try to find compatible waves to attach the move lines to, if wave grouping is enabled."""
        lines_nearest_parent_locations = defaultdict(lambda: self.env['stock.location'])
        batchable_line_ids = OrderedSet()
        for line in self:
            if not line._is_auto_wave_batchable():
                continue
            if not line.picking_type_id.wave_group_by_location:
                batchable_line_ids.add(line.id)
                continue
            for location in reversed(line.picking_type_id.wave_location_ids):
                if line.location_id._child_of(location):
                    lines_nearest_parent_locations[line] = location
                    batchable_line_ids.add(line.id)
                    break
        batchable_lines = self.env['stock.move.line'].browse(batchable_line_ids)

        remaining_line_ids = batchable_lines._auto_group_lines_to_existing_waves(nearest_parent_locations=lines_nearest_parent_locations)
        remaining_lines = self.env['stock.move.line'].browse(remaining_line_ids)
        if remaining_lines:
            remaining_lines._auto_group_lines_together(nearest_parent_locations=lines_nearest_parent_locations)

    def _auto_group_lines_to_existing_waves(self, nearest_parent_locations=False):
        picking_types = self.mapped('picking_type_id')
        remaining_lines = OrderedSet()
        for picking_type in picking_types:
            lines = self.filtered(lambda l: l.picking_type_id == picking_type)
            if lines:
                domain = [
                    ('state', 'not in', ('done', 'cancel') if picking_type.batch_auto_confirm else ('draft',)),
                    ('picking_type_id', '=', picking_type.id),
                    ('company_id', 'in', self.mapped('company_id').ids),
                    ('is_wave', '=', True)
                ]
                if picking_type.batch_group_by_partner:
                    domain = expression.AND([domain, [('picking_ids.partner_id', 'in', lines.move_id.partner_id.ids)]])
                if picking_type.batch_group_by_destination:
                    domain = expression.AND([domain, [('picking_ids.partner_id.country_id', 'in', lines.move_id.partner_id.country_id.ids)]])
                if picking_type.batch_group_by_src_loc:
                    domain = expression.AND([domain, [('picking_ids.location_id', 'in', lines.location_id.ids)]])
                if picking_type.batch_group_by_dest_loc:
                    domain = expression.AND([domain, [('picking_ids.location_dest_id', 'in', lines.location_dest_id.ids)]])

                potential_waves = self.env['stock.picking.batch'].search(domain)
                wave_to_lines = defaultdict(set)
                wave_to_new_moves = defaultdict(set)
                waves_to_new_pickings = defaultdict(set)
                waves_weight = defaultdict(float)

                waves_nearest_parent_locations = defaultdict(int)
                if picking_type.wave_group_by_location:
                    for wave in potential_waves:
                        for wave_location in reversed(picking_type.wave_location_ids):
                            if all(loc._child_of(wave_location) for loc in wave.move_line_ids.location_id):
                                waves_nearest_parent_locations[wave] = wave_location.id
                                break
                    potential_waves = potential_waves.filtered(lambda wave: wave in waves_nearest_parent_locations)

                for line in lines:
                    wave_found = False
                    for wave in potential_waves:
                        if line.company_id != wave.company_id:
                            continue
                        if picking_type.batch_group_by_partner and line.move_id.partner_id != wave.picking_ids.partner_id:
                            continue
                        if picking_type.batch_group_by_destination and line.move_id.partner_id.country_id != wave.picking_ids.partner_id.country_id:
                            continue
                        if picking_type.batch_group_by_src_loc and line.location_id != wave.picking_ids.location_id:
                            continue
                        if picking_type.batch_group_by_dest_loc and line.location_dest_id != wave.picking_ids.location_dest_id:
                            continue
                        if picking_type.wave_group_by_product and line.product_id != wave.move_line_ids.product_id:
                            continue
                        if picking_type.wave_group_by_category and line.product_categ_id != wave.move_line_ids.product_categ_id:
                            continue
                        if picking_type.wave_group_by_location and waves_nearest_parent_locations[wave] != nearest_parent_locations[line].id:
                            continue

                        other_move_ids = wave_to_new_moves[wave]
                        other_pickings = waves_to_new_pickings[wave]
                        wave_moves = set(wave.move_line_ids.mapped('move_id.id'))
                        wave_pickings = set(wave.move_line_ids.mapped('picking_id.id'))
                        if not wave._is_line_auto_mergeable(
                            line.move_id.id not in wave_moves and line.move_id.id not in other_move_ids and len(other_move_ids) + 1,
                            line.picking_id.id not in wave_pickings and line.picking_id.id not in other_pickings and len(other_pickings) + 1,
                            waves_weight[wave] + line.product_id.weight * line.quantity_product_uom
                        ):
                            continue

                        if line.move_id.id not in wave_moves:
                            wave_to_new_moves[wave].add(line.move_id.id)
                        if line.picking_id.id not in wave_pickings:
                            waves_to_new_pickings[wave].add(line.picking_id.id)
                        waves_weight[wave] += line.product_id.weight * line.quantity_product_uom
                        wave_to_lines[wave].add(line.id)
                        wave_found = True
                        break
                    if not wave_found:
                        remaining_lines.add(line.id)
                for wave, line_ids in wave_to_lines.items():
                    lines = self.env['stock.move.line'].browse(line_ids)
                    lines._add_to_wave(wave)
        return remaining_lines

    def _auto_group_lines_together(self, nearest_parent_locations=False):
        picking_types = self.picking_type_id
        for picking_type in picking_types:
            lines = self.filtered(lambda l: l.picking_type_id == picking_type)
            domain = [
                ('company_id', 'in', self.company_id.ids),
                ('picking_id.state', '=', 'assigned'),
                ('picking_type_id', '=', picking_type.id),
                '|',
                ('batch_id', '=', False),
                ('batch_id.is_wave', '=', False)
            ]
            if picking_type.batch_group_by_partner:
                domain = expression.AND([domain, [('move_id.partner_id', 'in', lines.move_id.partner_id.ids)]])
            if picking_type.batch_group_by_destination:
                domain = expression.AND([domain, [('move_id.partner_id.country_id', 'in', lines.move_id.partner_id.country_id.ids)]])
            if picking_type.batch_group_by_src_loc:
                domain = expression.AND([domain, [('location_id', 'in', lines.location_id.ids)]])
            if picking_type.batch_group_by_dest_loc:
                domain = expression.AND([domain, [('location_dest_id', 'in', lines.location_dest_id.ids)]])
            if picking_type.wave_group_by_product:
                domain = expression.AND([domain, [('product_id', 'in', lines.product_id.ids)]])
            if picking_type.wave_group_by_category:
                domain = expression.AND([domain, [('product_categ_id', 'in', lines.product_categ_id.ids)]])
            if picking_type.wave_group_by_location:
                domain = expression.AND([domain, [('location_id', 'child_of', picking_type.wave_location_ids.ids)]])

            potential_lines = self.env['stock.move.line'].search(domain)
            lines_nearest_parent_locations = defaultdict(int)
            if picking_type.wave_group_by_location:
                for line in potential_lines:
                    for location in reversed(picking_type.wave_location_ids):
                        if line.location_id._child_of(location):
                            lines_nearest_parent_locations[line] = location.id
                            break

            line_to_lines = defaultdict(set)
            matched_lines = set()
            remaining_line_ids = OrderedSet()
            iters = 0
            for line in lines:
                lines_found = False
                if line.id in matched_lines:
                    continue
                for potential_line in potential_lines:
                    iters += 1
                    if line.id == potential_line.id:
                        continue
                    if line.company_id != potential_line.company_id:
                        continue
                    if picking_type.batch_group_by_partner and line.move_id.partner_id != potential_line.move_id.partner_id:
                        continue
                    if picking_type.batch_group_by_destination and line.move_id.partner_id.country_id != potential_line.move_id.partner_id.country_id:
                        continue
                    if picking_type.batch_group_by_src_loc and line.location_id != potential_line.location_id:
                        continue
                    if picking_type.batch_group_by_dest_loc and line.location_dest_id != potential_line.location_dest_id:
                        continue
                    if picking_type.wave_group_by_product and line.product_id != potential_line.product_id:
                        continue
                    if picking_type.wave_group_by_category and line.product_categ_id != potential_line.product_categ_id:
                        continue
                    if picking_type.wave_group_by_location and lines_nearest_parent_locations[potential_line] != nearest_parent_locations[line].id:
                        continue
                    line_to_lines[line].add(potential_line.id)
                    matched_lines.add(potential_line.id)
                    lines_found = True
                if not lines_found:
                    remaining_line_ids.add(line.id)
            for line, potential_line_ids in line_to_lines.items():
                if line.batch_id.is_wave:
                    continue
                potential_lines = self.env['stock.move.line'].browse(potential_line_ids)
                potential_lines = potential_lines.filtered(lambda l: not l.batch_id.is_wave)
                potential_lines |= line
                i = 0
                # We want to make sure that batch/wave limits specified in the picking type are respected.
                # We want also to reduce picking splits as much as possible. So we try to group as much as possible by sorting the lines by picking and move.
                potential_lines = potential_lines.sorted(key=lambda l: (l.picking_id.id, l.move_id.id))
                while i < len(potential_lines):
                    new_wave = self.env['stock.picking.batch'].create({
                        'is_wave': True,
                        'picking_type_id': self.picking_type_id and self.picking_type_id[0].id,
                        'user_id': self.env.context.get('active_owner_id'),
                        'description': line._get_auto_wave_description(nearest_parent_locations[line]),
                    })
                    wave_new_move_ids = set()
                    wave_new_picking_ids = set()
                    wave_new_line_ids = set()
                    wave_weight = 0
                    j = i
                    while j < len(potential_lines):
                        wave_new_move_ids.add(potential_lines[j].move_id.id)
                        wave_new_picking_ids.add(potential_lines[j].picking_id.id)
                        wave_weight += potential_lines[j].product_id.weight * potential_lines[j].quantity_product_uom
                        if not new_wave._is_line_auto_mergeable(
                            len(wave_new_move_ids),
                            len(wave_new_picking_ids),
                            wave_weight
                        ):
                            break
                        wave_new_line_ids.add(potential_lines[j].id)
                        j += 1
                    if wave_new_line_ids:
                        wave_new_lines = self.env['stock.move.line'].browse(wave_new_line_ids)
                        wave_new_lines._add_to_wave(new_wave)
                        i = j - 1
                    i += 1

            remaining_lines = self.env['stock.move.line'].browse(remaining_line_ids)
            for line in remaining_lines:
                line._add_to_wave(description=line._get_auto_wave_description(nearest_parent_locations[line]))

    def _get_auto_wave_description(self, nearest_parent_location=False):
        self.ensure_one()
        description = self.picking_id._get_auto_batch_description()
        description_items = []
        if description:
            description_items.append(description)

        if self.picking_type_id.wave_group_by_product:
            description_items.append(self.product_id.display_name)
        if self.picking_type_id.wave_group_by_category:
            description_items.append(self.product_categ_id.display_name)
        if self.picking_type_id.wave_group_by_location:
            description_items.append(nearest_parent_location.complete_name)

        description = ', '.join(description_items)
        return description
