# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _get_detail_lines_extra_cost(self, qty_done):
        detail_lines = super()._get_detail_lines_extra_cost(qty_done)

        currency_id = self.company_id.currency_id
        if not currency_id.is_zero(self.extra_cost):
            detail_lines.append("Subcontracting cost: %.2f %s/%s - %.2f %s" % (
                currency_id.round(self.extra_cost), currency_id.symbol,
                self.product_uom_id.name, currency_id.round(self.extra_cost * qty_done),
                currency_id.symbol
            ))
        return detail_lines
