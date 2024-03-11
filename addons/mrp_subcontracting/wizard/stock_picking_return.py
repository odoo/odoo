# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    subcontract_location_id = fields.Many2one('stock.location', compute='_compute_subcontract_location_id')

    @api.depends('picking_id')
    def _compute_subcontract_location_id(self):
        for record in self:
            record.subcontract_location_id = record.picking_id.partner_id.with_company(
                record.picking_id.company_id
            ).property_stock_subcontractor

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        res = super(ReturnPicking, self)._onchange_picking_id()
        if any(return_line.quantity > 0 and return_line.move_id.is_subcontract for return_line in self.product_return_moves):
            self.location_id = self.picking_id.partner_id.with_company(self.picking_id.company_id).property_stock_subcontractor
        return res

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super(ReturnPicking, self)._prepare_move_default_values(return_line, new_picking)
        vals['is_subcontract'] = False
        return vals
