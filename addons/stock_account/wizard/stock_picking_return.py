# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund = fields.Boolean(string="Update quantities on SO/PO", default=True,
        help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        vals['to_refund'] = self.to_refund
        return vals
