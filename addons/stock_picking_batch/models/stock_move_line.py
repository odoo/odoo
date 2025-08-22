# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, Command, fields, models
from odoo.osv import expression
from odoo.tools.float_utils import float_is_zero
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
        split_pickings_ids = set()
        for picking, lines in line_by_picking.items():
            # Move the entire picking if all the line are taken
            line_by_move = defaultdict(lambda: self.env['stock.move.line'])
            qty_by_move = defaultdict(float)
            for line in lines:
                move = line.move_id
                line_by_move[move] |= line
                qty = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id, rounding_method='HALF-UP')
                qty_by_move[line.move_id] += qty

            # If all moves are to be transferred to the wave, link the picking to the wave
            if lines == picking.move_line_ids and lines.move_id == picking.move_ids:
                add_all_moves = True
                for move, qty in qty_by_move.items():
                    if float_is_zero(qty, precision_rounding=move.product_uom.rounding):
                        add_all_moves = False
                        break
                if add_all_moves:
                    wave.picking_ids = [Command.link(picking.id)]
                    continue

            # Split the picking in two part to extract only line that are taken on the wave
            picking_to_wave_vals = picking.copy_data({
                'move_ids': [],
                'move_line_ids': [],
                'batch_id': wave.id,
                'scheduled_date': picking.scheduled_date,
            })[0]
            split_pickings_ids.add(picking.id)
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
            split_pickings = self.env['stock.picking'].browse(split_pickings_ids) | self.env['stock.picking'].create(picking_to_wave_vals_list)
            split_pickings._add_to_wave_post_picking_split_hook()
        if wave.picking_type_id.batch_auto_confirm:
            wave.action_confirm()

    def _is_auto_waveable(self):
        self.ensure_one()
        if not self.picking_id \
           or (self.picking_id.state != 'assigned' or float_is_zero(self.quantity, precision_rounding=self.product_uom_id.rounding)) and not self.env.context.get('skip_auto_waveable')  \
           or self.batch_id.is_wave \
           or not self.picking_type_id._is_auto_wave_grouped() \
           or (self.picking_type_id.wave_group_by_category and self.product_id.categ_id not in self.picking_type_id.wave_category_ids):  # noqa: SIM103
            return False
        return True

    def _auto_wave(self):
        """ Try to find compatible waves to attach the move lines to, otherwise create new waves when possible/appropriate. """
        wave_locs_by_picking_type = {}
        for picking_type in self.picking_type_id:
            if not picking_type.wave_group_by_location:
                continue
            if picking_type in wave_locs_by_picking_type:
                continue
            wave_locs_by_picking_type[picking_type] = set(picking_type.wave_location_ids.ids)
        lines_nearest_parent_locations = defaultdict(lambda: self.env['stock.location'])
        batchable_line_ids = OrderedSet()
        for line in self:
            if not line._is_auto_waveable():
                continue
            if not line.picking_type_id.wave_group_by_location:
                batchable_line_ids.add(line.id)
                continue
            # We want to find the most descendant location in the wave locations list that is a parent of the line location.
            # Since the wave locations are ordered by complete_name (from the most descendant to the most ancestor), we can iterate in reverse order.
            wave_locs_set = wave_locs_by_picking_type[line.picking_type_id]
            loc = line.location_id
            while (loc):
                if loc.id in wave_locs_set:
                    lines_nearest_parent_locations[line] = loc
                    batchable_line_ids.add(line.id)
                    break
                loc = loc.location_id
        batchable_lines = self.env['stock.move.line'].browse(batchable_line_ids)

        remaining_line_ids = batchable_lines._auto_wave_lines_into_existing_waves(nearest_parent_locations=lines_nearest_parent_locations)
        remaining_lines = self.env['stock.move.line'].browse(remaining_line_ids)
        if remaining_lines:
            remaining_lines._auto_wave_lines_into_new_waves(nearest_parent_locations=lines_nearest_parent_locations)

    def _auto_wave_lines_into_existing_waves(self, nearest_parent_locations=False):
        """ Try to add move lines to existing waves if possible, return move lines of which no appropriate waves were found to link to
         :param nearest_parent_locations (defaultdict): the key is the move line and the value is the nearest parent location in the wave locations list"""
        remaining_lines = OrderedSet()
        for (picking_type, lines) in self.grouped(lambda l: l.picking_type_id).items():
            if lines:
                domain = [
                    ('picking_type_id', '=', picking_type.id),
                    ('company_id', 'in', lines.mapped('company_id').ids),
                    ('is_wave', '=', True)
                ]
                if picking_type.batch_auto_confirm:
                    domain = expression.AND([domain, [('state', 'not in', ['done', 'cancel'])]])
                else:
                    domain = expression.AND([domain, [('state', '=', 'draft')]])
                if picking_type.batch_group_by_partner:
                    domain = expression.AND([domain, [('picking_ids.partner_id', 'in', lines.move_id.partner_id.ids)]])
                if picking_type.batch_group_by_destination:
                    domain = expression.AND([domain, [('picking_ids.partner_id.country_id', 'in', lines.move_id.partner_id.country_id.ids)]])
                if picking_type.batch_group_by_src_loc:
                    domain = expression.AND([domain, [('picking_ids.location_id', 'in', lines.location_id.ids)]])
                if picking_type.batch_group_by_dest_loc:
                    domain = expression.AND([domain, [('picking_ids.location_dest_id', 'in', lines.location_dest_id.ids)]])

                potential_waves = self.env['stock.picking.batch'].search(domain)
                wave_to_new_lines = defaultdict(set)

                # These dictionaries are used to enforce batch max lines/transfers/weight limits
                # Each time a line is matched to a wave, we update the corresponding values
                wave_to_new_moves = defaultdict(set)
                waves_to_new_pickings = defaultdict(set)
                waves_new_extra_weight = defaultdict(float)

                waves_nearest_parent_locations = defaultdict(int)
                if picking_type.wave_group_by_location:
                    valid_wave_ids = set()
                    # We want to find the most descendant location in the wave locations list that is a parent of all the lines in each wave.
                    # We also want to exclude waves that have lines that are not in these locations.
                    for wave in potential_waves:
                        for wave_location in reversed(picking_type.wave_location_ids):
                            if all(loc._child_of(wave_location) for loc in wave.move_line_ids.location_id):
                                waves_nearest_parent_locations[wave] = wave_location.id
                                valid_wave_ids.add(wave.id)
                                break
                    potential_waves = self.env['stock.picking.batch'].browse(valid_wave_ids)

                for line in lines:
                    wave_found = False
                    for wave in potential_waves:
                        if line.company_id != wave.company_id \
                        or (picking_type.batch_group_by_partner and line.move_id.partner_id != wave.picking_ids.partner_id) \
                        or (picking_type.batch_group_by_destination and line.move_id.partner_id.country_id != wave.picking_ids.partner_id.country_id) \
                        or (picking_type.batch_group_by_src_loc and line.location_id != wave.picking_ids.location_id) \
                        or (picking_type.batch_group_by_dest_loc and line.location_dest_id != wave.picking_ids.location_dest_id) \
                        or (picking_type.wave_group_by_product and line.product_id != wave.move_line_ids.product_id) \
                        or (picking_type.wave_group_by_category and line.product_id.categ_id != wave.move_line_ids.product_id.categ_id) \
                        or (picking_type.wave_group_by_location and waves_nearest_parent_locations[wave] != nearest_parent_locations[line].id):
                            continue

                        wave_new_move_ids = wave_to_new_moves[wave]
                        wave_new_picking_ids = waves_to_new_pickings[wave]
                        wave_move_ids = set(wave.move_line_ids.mapped('move_id.id'))
                        wave_picking_ids = set(wave.move_line_ids.mapped('picking_id.id'))
                        # `is_line_auto_mergeable` is a method that checks if the line can be added to the wave without exceeding the limits
                        # It takes as arguments the number of new moves that will be added to the wave, the number of new pickings that will be added to the wave
                        # and the extra weight that will be added to the wave. So we need to check that the move/picking of the line is not already in the wave
                        # so that we don't count them as new moves/pickings.
                        if not wave._is_line_auto_mergeable(
                            line.move_id.id not in wave_move_ids and line.move_id.id not in wave_new_move_ids and len(wave_new_move_ids) + 1,
                            line.picking_id.id not in wave_picking_ids and line.picking_id.id not in wave_new_picking_ids and len(wave_new_picking_ids) + 1,
                            waves_new_extra_weight[wave] + line.product_id.weight * line.quantity_product_uom
                        ):
                            continue

                        if line.move_id.id not in wave_move_ids:
                            wave_to_new_moves[wave].add(line.move_id.id)
                        if line.picking_id.id not in wave_picking_ids:
                            waves_to_new_pickings[wave].add(line.picking_id.id)
                        waves_new_extra_weight[wave] += line.product_id.weight * line.quantity_product_uom
                        wave_to_new_lines[wave].add(line.id)
                        wave_found = True
                        break
                    if not wave_found:
                        remaining_lines.add(line.id)
                for wave, line_ids in wave_to_new_lines.items():
                    lines = self.env['stock.move.line'].browse(line_ids)
                    lines._add_to_wave(wave)
        return list(remaining_lines)

    def _auto_wave_lines_into_new_waves(self, nearest_parent_locations=False):
        """ Create new waves for the move lines that could not be added to existing waves. """
        picking_types = self.picking_type_id
        for picking_type in picking_types:
            lines = self.filtered(lambda l: l.picking_type_id == picking_type)
            domain = [
                ('id', 'in', lines.ids),
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
                domain = expression.AND([domain, [('product_id.categ_id', 'in', lines.product_id.categ_id.ids)]])
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
            for line in lines:
                lines_found = False
                if line.id in matched_lines:
                    continue
                for potential_line in potential_lines:
                    if line.id == potential_line.id \
                    or line.company_id != potential_line.company_id \
                    or (picking_type.batch_group_by_partner and line.move_id.partner_id != potential_line.move_id.partner_id) \
                    or (picking_type.batch_group_by_destination and line.move_id.partner_id.country_id != potential_line.move_id.partner_id.country_id) \
                    or (picking_type.batch_group_by_src_loc and line.location_id != potential_line.location_id) \
                    or (picking_type.batch_group_by_dest_loc and line.location_dest_id != potential_line.location_dest_id) \
                    or (picking_type.wave_group_by_product and line.product_id != potential_line.product_id) \
                    or (picking_type.wave_group_by_category and line.product_id.categ_id != potential_line.product_id.categ_id) \
                    or (picking_type.wave_group_by_location and lines_nearest_parent_locations[potential_line] != nearest_parent_locations[line].id):
                        continue

                    line_to_lines[line].add(potential_line.id)
                    matched_lines.add(potential_line.id)
                    lines_found = True
                if not lines_found:
                    remaining_line_ids.add(line.id)

            for line, potential_line_ids in line_to_lines.items():
                if line.batch_id.is_wave:
                    continue

                potential_lines = self.env['stock.move.line'].browse(potential_line_ids | {line.id})

                # We want to make sure that batch/wave limits specified in the picking type are respected.
                # We want also to reduce picking splits as much as possible. So we try to group as much as possible by sorting the lines by picking and move.
                potential_lines = potential_lines.sorted(key=lambda l: (l.picking_id.id, l.move_id.id))

                while potential_lines:
                    new_wave = self.env['stock.picking.batch'].create({
                        'is_wave': True,
                        'picking_type_id': picking_type.id,
                        'description': line._get_auto_wave_description(nearest_parent_locations[line]),
                    })
                    wave_move_ids = set()
                    wave_picking_ids = set()
                    wave_weight = 0

                    wave_line_ids = set()

                    for potential_line in potential_lines:
                        if potential_line.batch_id.is_wave:
                            continue
                        wave_move_ids.add(potential_line.move_id.id)
                        wave_picking_ids.add(potential_line.picking_id.id)
                        wave_weight += potential_line.product_id.weight * potential_line.quantity_product_uom
                        if new_wave._is_line_auto_mergeable(
                            len(wave_move_ids),
                            len(wave_picking_ids),
                            wave_weight
                        ):
                            wave_line_ids.add(potential_line.id)
                        else:
                            break
                    wave_lines = self.env['stock.move.line'].browse(wave_line_ids)
                    wave_lines._add_to_wave(new_wave)
                    potential_lines -= wave_lines

            remaining_lines = self.env['stock.move.line'].browse(remaining_line_ids)
            remaining_waves = self.env['stock.picking.batch'].create([{
                'is_wave': True,
                'picking_type_id': picking_type.id,
                'description': remaining_line._get_auto_wave_description(nearest_parent_locations[remaining_line]),
            } for remaining_line in remaining_lines])
            for (line, wave) in zip(remaining_lines, remaining_waves):
                line._add_to_wave(wave)

    def _get_auto_wave_description(self, nearest_parent_location=False):
        self.ensure_one()
        description = self.picking_id._get_auto_batch_description()
        description_items = []
        if description:
            description_items.append(description)

        if self.picking_type_id.wave_group_by_product:
            description_items.append(self.product_id.display_name)
        if self.picking_type_id.wave_group_by_category:
            description_items.append(self.product_id.categ_id.complete_name)
        if self.picking_type_id.wave_group_by_location:
            description_items.append(nearest_parent_location.complete_name)

        description = ', '.join(description_items)
        return description
