# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockUnbuildGreaterThanProduced(models.TransientModel):
    _name = 'stock.unbuild.greater.than.produced'
    _description = 'Stock Unbuild Greater Than Produced'

    unbuild_id = fields.Many2one('mrp.unbuild', 'Unbuild')
    produced_quantity = fields.Float("Produced Quantity")
    old_unbuild_quantity = fields.Float("Already Unbuild")
    unbuild_quantity = fields.Float("Unbuild Qty")

    def action_done(self):
        self.ensure_one()
        return self.unbuild_id.with_context(skip_more_then_produced_check=True).action_unbuild()
