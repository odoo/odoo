# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, _, api


class SaleCouponProgram(models.Model):
    _inherit = "sale.coupon.program"

    def _filter_not_ordered_reward_programs(self, order):
        """
        Returns the programs when the reward is actually in the order lines
        """
        programs = super(SaleCouponProgram, self)._filter_not_ordered_reward_programs(order)
        # Do not filter on free delivery programs. As delivery_unset is called everywhere (which is
        # rather stupid), the delivery line is unliked to be created again instead of writing on it to
        # modify the price_unit. That way, the reward is unlink and is not set back again.
        return programs

    def _check_promo_code(self, order, coupon_code):
        if self.reward_type == 'free_shipping' and not order.order_line.filtered(lambda line: line.is_delivery):
            return {'error': _('The shipping costs are not in the order lines.')}
        return super(SaleCouponProgram, self)._check_promo_code(order, coupon_code)

    @api.model
    def _filter_on_mimimum_amount(self, order):
        # To get actual total amount of SO without any reward or discount
        # We exclude any line of the order that is a delivery
        # get the round function of the currency: we want to imitate what the sale.order.amount is (computed field)
        round_curr = order.pricelist_id.currency_id.round
        order_lines = order.order_line.filtered(lambda l: not l.is_delivery)
        order_amount = round_curr(sum(order_lines.mapped('price_subtotal')))
        order_tax = round_curr(sum(order_lines.mapped('price_tax')))
        discounted_amount = sum(order_lines.filtered(lambda line: line.is_reward_line).mapped('price_total'))
        untaxed_amount = order_amount - discounted_amount
        return self.filtered(lambda program:
            program.rule_minimum_amount_tax_inclusion == 'tax_included' and
            program._compute_program_amount('rule_minimum_amount', order.currency_id) <= untaxed_amount + order_tax or
            program.rule_minimum_amount_tax_inclusion == 'tax_excluded' and
            program._compute_program_amount('rule_minimum_amount', order.currency_id) <= untaxed_amount)
