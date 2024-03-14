# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, fields, models
from odoo import Command, api
from odoo.tools.float_utils import float_compare
from odoo.osv import expression

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

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # a read_group cannot be performed if the move lines are grouped by picking_type_id, since it is a computed field
        # so it is done on two steps: first, the corresponding stock pickings of the stock move lines matching the domain is fetched
        # then the stock pickings are grouped by picking type
        # the result of read_group on stock pickings is returned after adjusting the count and the domain
        if 'picking_type_id' in groupby:
            groupby.remove('picking_type_id')
            groupby.append('picking_id')
            move_lines = super().search(domain)
            pickings = [move_line.picking_id.id for move_line in move_lines]
            grouped_stock_moves = self.env['stock.picking'].read_group(domain=[('id', 'in', pickings)], fields=[], groupby=['picking_type_id'], offset=0, limit=None, orderby=False, lazy=True)
            for group in grouped_stock_moves:
                if group['picking_type_id']:
                    group['__domain'] = [('picking_id', term[1], term[2]) if 'id' in term else term for term in group['__domain']]
                    group['__domain'] = expression.AND([group['__domain'], domain])
                    group['picking_type_id_count'] = super().search_count(group['__domain'])
            grouped_stock_moves = [group for group in grouped_stock_moves if group['picking_type_id']]
            return grouped_stock_moves
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def _find_auto_wave(self):
        # Try to find compatible waves to attach the move lines to, if wave grouping is enabled
        line_by_wave = defaultdict(lambda: self.env['stock.move.line'])
        for line in self:
            if line.batch_id.is_wave or (line.picking_type_id.should_group_waves == 'fully_available' and line.state != 'assigned'):
                continue
            if line.picking_type_id.wave_grouping:
                nearest_parent_location = line.env['stock.location']
                if line.picking_type_id.wave_group_by_location:
                    nearest_parent_locations = line.env['stock.location'].sudo().search(domain=[('id', 'in', line.picking_type_id.wave_location_ids.ids), ('id', 'parent_of', line.location_id.id)])
                    if len(nearest_parent_locations) == 0:
                        continue
                    nearest_parent_locations = nearest_parent_locations.sorted(key=lambda l: len(l.complete_name), reverse=True)
                    nearest_parent_location = nearest_parent_locations[0]
                possible_waves = line._get_possible_waves(nearest_parent_location)
                compatible_wave_found = False
                for wave in possible_waves:
                    if wave._is_line_auto_mergeable(line):
                        line_by_wave[wave] |= line
                        compatible_wave_found = True

                # If no wave was found, try fo find compatible lines and put them in a new wave.
                possible_lines = line.env['stock.move.line'].sudo().search(line._get_possible_lines_domain(nearest_parent_location))
                if not line.picking_type_id.wave_group_by_location:
                    possible_lines |= line
                    possible_lines._add_to_wave(description=line._get_new_wave_description())
                else:
                    possible_lines = possible_lines.sorted(key=lambda l: len(l.location_id.complete_name), reverse=True)
                    if len(possible_lines) == 0:
                        if not compatible_wave_found:
                            line._add_to_wave(description=line._get_new_wave_description(nearest_parent_location))
                    elif not compatible_wave_found:
                        grouped_lines = line.env['stock.move.line']
                        grouped_lines |= possible_lines[0]
                        grouped_lines |= line
                        grouped_lines._add_to_wave(description=line._get_new_wave_description(nearest_parent_location))

        for wave, lines in line_by_wave.items():
            lines._add_to_wave(wave)

    def _get_possible_waves(self, nearest_parent_location=False):
        self.ensure_one()

        domain = [
            ('state', 'not in', ('done', 'cancel') if self.picking_type_id.batch_auto_confirm else ('draft',)),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('company_id', '=', self.company_id.id if self.company_id else False),
            ('batch_id.is_wave', '=', True),
        ]
        if self.picking_type_id.batch_group_by_partner:
            domain = expression.AND([domain, [('batch_id.picking_ids.partner_id', '=', self.picking_id.partner_id.id)]])
        if self.picking_type_id.batch_group_by_destination:
            domain = expression.AND([domain, [('batch_id.picking_ids.partner_id.country_id', '=', self.picking_id.partner_id.country_id.id)]])
        if self.picking_type_id.batch_group_by_src_loc:
            domain = expression.AND([domain, [('batch_id.picking_ids.location_id', '=', self.picking_id.location_id.id)]])
        if self.picking_type_id.batch_group_by_dest_loc:
            domain = expression.AND([domain, [('batch_id.picking_ids.location_dest_id', '=', self.picking_id.location_dest_id.id)]])

        groupby = ['batch_id']

        if self.picking_type_id.wave_group_by_product:
            groupby.append('product_id')
        if self.picking_type_id.wave_group_by_category:
            groupby.append('product_id.categ_id')

        # Because move_ids field on stock.picking.batch model is not stored, we use read_group and then filter incompatible waves
        grouped_lines = self.env['stock.move.line'].read_group(domain=domain, fields=['id'], groupby=groupby, lazy=False)
        seen_waves = set()
        waves_to_remove = []
        for group in grouped_lines:
            if group['batch_id'] not in seen_waves:
                seen_waves.add(group['batch_id'])
            else:
                waves_to_remove.append(group['batch_id'])
        grouped_lines = [group for group in grouped_lines if group['batch_id'] not in waves_to_remove]
        if self.picking_type_id.wave_group_by_product:
            grouped_lines = [group for group in grouped_lines if group['product_id'][0] == self.product_id.id]
        if self.picking_type_id.wave_group_by_category:
            grouped_lines = [group for group in grouped_lines if group['product_id.categ_id'][0] == self.product_id.categ_id.id]

        possible_waves = self.env['stock.picking.batch']
        for group in grouped_lines:
            possible_waves |= self.env['stock.picking.batch'].browse(group['batch_id'][0])

        if self.picking_type_id.wave_group_by_location and nearest_parent_location:
            for wave in possible_waves:
                locations_search_domain = [('id', 'in', self.picking_type_id.wave_location_ids.ids)]
                for location in wave.move_line_ids.location_id:
                    locations_search_domain = expression.AND([locations_search_domain, [('id', 'parent_of', location.id)]])
                wave_parent_locations = self.env['stock.location'].sudo().search(locations_search_domain)
                wave_parent_locations = wave_parent_locations.sorted(key=lambda l: len(l.complete_name), reverse=True)
                wave_nearest_parent_location = wave_parent_locations[0]
                if wave_nearest_parent_location != nearest_parent_location:
                    possible_waves -= wave
        return possible_waves

    def _get_possible_lines_domain(self, nearest_parent_location=False):
        self.ensure_one()
        domain = [
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id if self.company_id else False),
            ('picking_id.state', '=', 'assigned'),
            ('picking_type_id', '=', self.picking_type_id.id),
            '|',
            ('batch_id', '=', False),
            ('batch_id.is_wave', '=', False)
        ]

        if self.picking_type_id.batch_group_by_partner:
            domain = expression.AND([domain, [('move_id.partner_id', '=', self.move_id.partner_id.id)]])
        if self.picking_type_id.batch_group_by_destination:
            domain = expression.AND([domain, [('move_id.partner_id.country_id', '=', self.move_id.partner_id.country_id.id)]])
        if self.picking_type_id.batch_group_by_src_loc:
            domain = expression.AND([domain, [('location_id', '=', self.location_id.id)]])
        if self.picking_type_id.batch_group_by_dest_loc:
            domain = expression.AND([domain, [('location_dest_id', '=', self.location_dest_id.id)]])
        if self.picking_type_id.wave_group_by_product:
            domain = expression.AND([domain, [('product_id', '=', self.product_id.id)]])
        if self.picking_type_id.wave_group_by_category:
            domain = expression.AND([domain, [('product_id.categ_id', '=', self.product_id.categ_id.id)]])
        if self.picking_type_id.wave_group_by_location and nearest_parent_location:
            # We want to get the lines that share the same parent location, however, we should exclude lines with a more specific (descendant) location
            # because they should be added to a more specific wave
            nearest_parent_children = self.env['stock.location'].sudo().search(
                [('id', 'child_of', nearest_parent_location.id), ('id', '!=', nearest_parent_location.id), ('id', 'in', self.picking_type_id.wave_location_ids.ids)])
            domain = expression.AND([domain, [('location_id', 'child_of', nearest_parent_location.id)]])
            domain = expression.AND([domain, ['!', ('location_id', 'child_of', nearest_parent_children.ids)]])
        return domain

    def _get_new_wave_description(self, nearest_parent_location=False):
        self.ensure_one()
        description = self.picking_id._get_new_batch_description()
        description_items = []
        if description:
            description_items.append(description)

        if self.picking_type_id.wave_group_by_product:
            description_items.append(self.product_id.display_name)
        if self.picking_type_id.wave_group_by_category:
            description_items.append(self.product_id.categ_id.display_name)
        if self.picking_type_id.wave_group_by_location:
            description_items.append(nearest_parent_location.complete_name)

        description = ', '.join(description_items)
        return description
