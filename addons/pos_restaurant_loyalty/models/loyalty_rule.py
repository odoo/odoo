from odoo import models


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    def _qualifying_lines(self, order, lines=None):
        """
        Split payment lines only move an amount between the origin order and the split
        payment orders. They are not goods, so they never count as units.
        mirror of *static/src/overrides/models/loyalty_rule.js* LoyaltyRule._qualifyingLines
        """
        qualifying = super()._qualifying_lines(order, lines)
        if self.reward_point_mode != 'unit':
            return qualifying
        split_payment_product = order.config_id.split_payment_product_id
        return qualifying.filtered(lambda line: line.product_id != split_payment_product)
