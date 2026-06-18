# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    def _counts_for_points(self, line):
        # Lines settling a sales order already earned their points on the S.O.
        return not line.sale_order_origin_id and super()._counts_for_points(line)
