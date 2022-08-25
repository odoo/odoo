# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_warehouse(self, subcontract_move):
        if subcontract_move.sale_line_id:
            return subcontract_move.sale_line_id.order_id.warehouse_id
        return super(StockPicking, self)._get_warehouse(subcontract_move)

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        res = super()._prepare_subcontract_mo_vals(subcontract_move, bom)
        if not res.get('picking_type_id') and subcontract_move.location_dest_id.usage == 'customer':
            # If the if-condition is respected, it means that `subcontract_move` is not
            # related to a specific warehouse. This can happen if, for instance, the user
            # confirms a PO with a subcontracted product that should be delivered to a
            # customer (dropshipping). In that case, we can use a default warehouse to
            # get the picking type
            default_warehouse = self.env['stock.warehouse'].search([('company_id', '=', subcontract_move.company_id.id)], limit=1)
            res['picking_type_id'] = default_warehouse.subcontracting_type_id.id,
        return res
