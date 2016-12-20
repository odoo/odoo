# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, _


class SaleCouponProgram(models.Model):
    _inherit = "sale.coupon.program"

    def _filter_not_ordered_reward_programs(self, order):
        """
        Returns the programs when the reward is actually in the order lines
        """
        programs = super(SaleCouponProgram, self)._filter_not_ordered_reward_programs(order)
        for program in self:
            if program.reward_type == 'free_shipping' and \
               not order.order_line.filtered(lambda line: line.is_delivery):
                programs -= program
        return programs

    def _check_promo_code(self, order, coupon_code):
        if self.reward_type == 'free_shipping' and not order.order_line.filtered(lambda line: line.is_delivery):
            return {'error': _('The shipping costs are not in the order lines.')}
        return super(SaleCouponProgram, self)._check_promo_code(order, coupon_code)

