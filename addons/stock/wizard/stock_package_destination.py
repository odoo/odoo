# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ChooseDestinationLocation(models.TransientModel):
    _name = 'stock.package.destination'
    _description = 'Stock Package Destination'

    picking_id = fields.Many2one('stock.picking', required=True)
    move_line_ids = fields.Many2many('stock.move.line', 'Products', compute='_compute_move_line_ids', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination location', required=True)
    filtered_location = fields.One2many(comodel_name='stock.location', compute='_filter_location')

    @api.depends('picking_id')
    def _compute_move_line_ids(self):
        for destination in self:
            destination.move_line_ids = destination.picking_id.move_line_ids.filtered(lambda l: l.qty_done > 0 and not l.result_package_id)

    @api.depends('move_line_ids')
    def _filter_location(self):
        for destination in self:
            destination.filtered_location = destination.move_line_ids.mapped('location_dest_id')

    def action_done(self):
        # set the same location on each move line and pass again in action_put_in_pack
        self.move_line_ids.location_dest_id = self.location_dest_id
        return self.picking_id.action_put_in_pack()
