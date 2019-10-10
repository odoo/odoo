# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, _


class Coupon(models.Model):
    _inherit = "coupon.coupon"

    def _check_coupon_code(self, order):
        if self.program_id.reward_type == 'free_shipping' and not order.order_line.filtered(lambda line: line.is_delivery):
            return {'error': _('The shipping costs are not in the order lines.')}
        return super(Coupon, self)._check_coupon_code(order)
