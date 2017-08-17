# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingToWave(models.TransientModel):
    _name = 'stock.picking.to.wave'
    _description = 'Add pickings to a picking wave'

    wave_id = fields.Many2one('stock.picking.wave', string='Picking Wave', required=True)

    @api.multi
    def attach_pickings(self):
        # use active_ids to add picking line to the selected wave
        self.ensure_one()
        picking_ids = self.env.context.get('active_ids')
        return self.env['stock.picking'].browse(picking_ids).write({'wave_id': self.wave_id.id})
