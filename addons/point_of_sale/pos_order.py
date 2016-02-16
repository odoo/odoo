# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.onchange('fiscal_position_id')
    def _compute_tax_id(self):
        """
        Trigger the recompute of the taxes if the fiscal position is changed on the Pos order.
        """
        for order in self:
            for line in order.lines:
                fpos = line.order_id.fiscal_position_id
                if fpos:
                    line.tax_ids = fpos.map_tax(line.product_id.taxes_id)
                else:
                    line.tax_ids = line.product_id.taxes_id
