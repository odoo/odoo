# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _inherit = 'loyalty.rule'

    def _is_condition_satisfied(self, order):
        applicable_lines = self._get_applicable_lines(order)
        if self.minimum_qty > 0:
            total_qty = sum(applicable_lines.mapped('qty'))
            if total_qty < self.minimum_qty:
                return False
        if self.minimum_amount > 0:
            tax_mode = 'price_subtotal_incl' if self.minimum_amount_tax_mode == 'incl' else 'price_subtotal_excl'
            total_amount = sum(applicable_lines.mapped(tax_mode))
            if total_amount < self.minimum_amount:
                return False
        return True

    def _get_applicable_lines(self, order):
        return order.lines.filtered(lambda line: not line.is_reward_line and (self.any_product or line.product_id in self.valid_product_ids))

    def _get_points_to_add(self, order):
        applicable_lines = self._get_applicable_lines(order)
        match self.reward_point_mode:
            case 'order':
                return self.reward_point_amount
            case 'money':
                total_amount = sum(applicable_lines.mapped('price_subtotal_incl'))
                return total_amount * self.reward_point_amount
            case 'unit':
                total_qty = sum(applicable_lines.mapped('qty'))
                return total_qty * self.reward_point_amount
            case _:
                return 0
