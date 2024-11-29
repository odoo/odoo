# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_picking_default_values(self):
        vals = super()._prepare_picking_default_values()
        if any(return_line.quantity > 0 and return_line.move_id.is_subcontract for return_line in self.product_return_moves):
            vals['location_dest_id'] = self.picking_id.partner_id.with_company(self.picking_id.company_id).property_stock_subcontractor.id
        return vals


class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        vals['is_subcontract'] = False
        return vals
