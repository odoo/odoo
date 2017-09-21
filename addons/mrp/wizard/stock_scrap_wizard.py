# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockScrapWizard(models.TransientModel):
    _name = 'stock.scrap.wizard'
    _inherit = 'stock.scrap.wizard'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order',
        help='Not to restrict or prefer quants, but informative.')
    unbuild_id = fields.Many2one('mrp.unbuild', 'Unbuild')

    @api.onchange('workorder_id')
    def onchange_workorder_id(self):
        if self.workorder_id:
            self.location_id = self.workorder_id.production_id.location_src_id.id

    @api.onchange('production_id')
    def onchange_production_id(self):
        if self.production_id:
            self.location_id = self.production_id.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) and self.production_id.location_src_id.id or self.production_id.location_dest_id.id

    def _prepare_scrap_vals(self):
        vals = super(StockScrapWizard, self)._prepare_scrap_vals()
        if self.production_id:
            vals['origin'] = vals['origin'] or self.production_id.name
            vals.update({'production_id': self.production_id.id})
        return vals

    def action_done(self):
        if self.unbuild_id:
            return self.unbuild_id.action_unbuild()
        return super(StockScrapWizard, self).action_done()
