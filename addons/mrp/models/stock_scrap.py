# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order',
        states={'done': [('readonly', True)]}, check_company=True)
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order',
        states={'done': [('readonly', True)]},
        help='Not to restrict or prefer quants, but informative.', check_company=True)

    @api.onchange('workorder_id')
    def _onchange_workorder_id(self):
        if self.workorder_id:
            self.location_id = self.workorder_id.production_id.location_src_id.id

    @api.onchange('production_id')
    def _onchange_production_id(self):
        if self.production_id:
            self.location_id = self.production_id.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) and self.production_id.location_src_id.id or self.production_id.location_dest_id.id

    def _prepare_move_values(self):
        vals = super(StockScrap, self)._prepare_move_values()
        if self.production_id:
            vals['origin'] = vals['origin'] or self.production_id.name
            if self.product_id in self.production_id.move_finished_ids.mapped('product_id'):
                vals.update({'production_id': self.production_id.id})
            else:
                vals.update({'raw_material_production_id': self.production_id.id})
        return vals

    @api.model
    def get_most_recent_move(self, moves):
        return sorted(moves, key=lambda m: m.date, reverse=True)[0]

    def do_scrap(self):
        res = super(StockScrap, self).do_scrap()
        for scrap in self:
            move_raw_material = scrap.production_id.move_raw_ids.filtered(
                lambda move: move.product_id.id == self.product_id.id)
            reserved_line = move_raw_material.move_line_ids.filtered(
                lambda line: line.lot_id.id == scrap.lot_id.id)
            reserved_quantity = reserved_line.product_uom_qty
            if move_raw_material.state in ['assigned', 'partially_available'] and reserved_quantity > 0.0:
                quantity_to_deduct = - min(self.scrap_qty, reserved_quantity)
                available_quantity = move_raw_material._get_available_quantity(scrap.location_id,
                                                                               lot_id=scrap.lot_id, strict=True)
                move_raw_material._update_reserved_quantity(quantity_to_deduct, available_quantity,
                                                            scrap.location_id, lot_id=scrap.lot_id)
                move_raw_material._recompute_state()
                previous_moves = move_raw_material.move_orig_ids.filtered(lambda m: m.state in ["done"])
                if previous_moves:
                    most_recent_move = self.get_most_recent_move(previous_moves)
                    most_recent_move.move_dest_ids |= scrap.move_id
        return res
