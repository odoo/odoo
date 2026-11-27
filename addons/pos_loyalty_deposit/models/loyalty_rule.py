# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    def _counts_for_points(self, line):
        return not line.product_id.is_deposit and super()._counts_for_points(line)
