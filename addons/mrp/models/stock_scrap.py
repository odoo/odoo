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
