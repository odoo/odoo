# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    quality_check_todo = fields.Boolean(compute='_compute_quality_check_todo')

    @api.depends('picking_ids')
    def _compute_quality_check_todo(self):
        for batch in self:
            batch.quality_check_todo = any(batch.picking_ids.mapped('quality_check_todo'))

    def action_open_quality_check_wizard(self):
        check_ids = self.picking_ids.check_ids.filtered(lambda check: check.quality_state == 'none')
        return check_ids.action_open_quality_check_wizard()
