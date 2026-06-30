# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_is_zero

class ReportMoOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_unit_cost(self, move):
        valuation_layers = move.sudo().stock_valuation_layer_ids
        layers_quantity = sum(valuation_layers.mapped('quantity'))
        if valuation_layers and not float_is_zero(layers_quantity, precision_rounding=valuation_layers.uom_id.rounding):
            unit_price = sum(valuation_layers.mapped('value')) / layers_quantity
            return move.product_id.uom_id._compute_price(unit_price, move.product_uom)
        return super()._get_unit_cost(move)
