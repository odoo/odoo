# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    stock_landed_cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost')

    def _should_impact_price_unit_receipt_value(self):
        res = super()._should_impact_price_unit_receipt_value()
        return res and not self.stock_landed_cost_id.vendor_bill_id
