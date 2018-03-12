# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingToBatch(models.TransientModel):
    _name = 'stock.picking.to.batch'
    _description = 'Batch Picking Lines'

    batch_id = fields.Many2one('stock.picking.batch', string='Batch Picking', required=True, oldname="wave_id")

    @api.multi
    def attach_pickings(self):
        # use active_ids to add picking line to the selected batch
        self.ensure_one()
        return self.env['stock.picking'].get_active_records().write({'batch_id': self.batch_id.id})
