# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv.expression import OR

class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        res = super(ReturnPicking, self)._onchange_picking_id()
        if not any(self.product_return_moves.filtered(lambda r: r.quantity > 0).move_id.mapped('is_subcontract')):
            return res
        subcontract_location = self.picking_id.partner_id.with_context(force_company=self.picking_id.company_id.id).property_stock_subcontractor
        self.location_id = subcontract_location.id
        domain_location = OR([
            ['|', ('id', '=', self.original_location_id.id), ('return_location', '=', True)],
            [('id', '=', subcontract_location.id)]
        ])
        if not res:
            res = {'domain': {'location_id': domain_location}}
        else:
            res['domain'] = {'location_id': domain_location}
        return res

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super(ReturnPicking, self)._prepare_move_default_values(return_line, new_picking)
        vals['is_subcontract'] = False
        return vals
