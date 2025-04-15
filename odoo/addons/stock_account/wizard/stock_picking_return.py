# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def default_get(self, default_fields):
        res = super(StockReturnPicking, self).default_get(default_fields)
        for i, k, vals in res.get('product_return_moves', []):
            vals.update({'to_refund': True})
        return res

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super(StockReturnPicking, self)._prepare_move_default_values(return_line, new_picking)
        if return_line.to_refund:
            vals['to_refund'] = True
        return vals


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund = fields.Boolean(string="Update quantities on SO/PO", default=True,
        help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
