# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    cost_method = fields.Char(related="product_id.product_tmpl_id.cost_method")
    unit_cost = fields.Float('Unit Cost', help="Unit cost of the product, used for inventory valuation.")
    theoretical_qty_bigger = fields.Boolean(compute="_compute_theoretical_qty_bigger")

    @api.model
    def create(self, vals):
        res = super(InventoryLine, self).create(vals)
        res.unit_cost = res.product_id.standard_price
        return res

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        self.ensure_one()
        res = super(InventoryLine, self)._get_move_values(qty, location_id, location_dest_id, out)
        if not out:
            res['price_unit'] = self.unit_cost
        return res

    def _compute_theoretical_qty_bigger(self):
        for line in self:
            line.theoretical_qty_bigger = float_compare(line.theoretical_qty, line.product_qty, precision_rounding=line.product_id.uom_id.rounding) == -1
