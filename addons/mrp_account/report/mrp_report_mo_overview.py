# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_unit_cost(self, move):
        if move.state == 'done' and not move.product_id.uom_id.is_zero(move._get_valued_qty()):
            price_unit = move._get_price_unit()
            return move.product_id.uom_id._compute_price(price_unit, move.product_uom)
        return super()._get_unit_cost(move)
