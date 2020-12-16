# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, _, api


class CouponProgram(models.Model):
    _inherit = "coupon.program"

    def _filter_not_ordered_reward_programs(self, order):
        """
        Returns the programs when the reward is actually in the order lines
        """
        programs = super(CouponProgram, self)._filter_not_ordered_reward_programs(order)
        # Do not filter on free delivery programs. As delivery_unset is called everywhere (which is
        # rather stupid), the delivery line is unliked to be created again instead of writing on it to
        # modify the price_unit. That way, the reward is unlink and is not set back again.
        return programs

    def _check_promo_code(self, order, coupon_code):
        if self.reward_type == 'free_shipping' and not any(line.is_delivery for line in order.order_line):
            return {'error': _('The shipping costs are not in the order lines.')}
        return super(CouponProgram, self)._check_promo_code(order, coupon_code)
