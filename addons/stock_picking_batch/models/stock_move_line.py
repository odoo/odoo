# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, fields, models
from odoo import Command


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    batch_id = fields.Many2one(related='picking_id.batch_id')

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

    def _add_to_wave(self, wave=False):
        """ Detach lines (and corresponding stock move from a picking to another). If wave is
        passed, attach new picking into it. If not attach line to their original picking.

        :param int wave: id of the wave picking on which to put the move lines. """

        if not wave:
            wave = self.env['stock.picking.batch'].create({
                'is_wave': True,
                'user_id': self.env.context.get('active_owner_id'),
            })
        line_by_picking = defaultdict(lambda: self.env['stock.move.line'])
        for line in self:
            # if not wave and line.orig_picking_id.is_wave:
                # continue
            line_by_picking[line.picking_id] |= line
        picking_to_wave_vals_list = []
        for picking, lines in line_by_picking.items():
            # Move the entire picking if all the line are taken
            if lines == picking.move_line_ids:
                wave.picking_ids = [Command.link(picking.id)]
                continue

            # Split the picking in two part to extract only line that are taken on the wave
            picking_to_wave_vals = picking.copy_data({
                'move_lines': [],
                'move_line_ids': [],
                'batch_id': wave.id,
            })[0]
            line_by_move = defaultdict(lambda: self.env['stock.move.line'])
            for line in lines:
                line_by_move[line.move_id] |= line
            for move, move_lines in line_by_move.items():
                picking_to_wave_vals['move_line_ids'] += [Command.link(line.id) for line in lines]
                # if all the line of a stock move are taken we change the picking on the stock move
                if move_lines == move.move_line_ids:
                    picking_to_wave_vals['move_lines'] += [Command.link(move.id)]
                    continue
                # Split the move
                qty = sum(lines.mapped('product_qty'))
                new_move = move._split(qty)
                new_move[0]['move_line_ids'] = [Command.set(move_lines.ids)]
                picking_to_wave_vals['move_lines'] += [Command.create(new_move[0])]

            picking_to_wave_vals_list.append(picking_to_wave_vals)

        if picking_to_wave_vals_list:
            self.env['stock.picking'].create(picking_to_wave_vals_list)
        wave.action_confirm()
