# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleCoupon(models.Model):
    _inherit = 'coupon.coupon'

    def _check_coupon_code(self, order):
        if self.program_id.website_id and self.program_id.website_id != order.website_id:
            return {'error': 'This coupon is not valid on this website.'}
        return super()._check_coupon_code(order)
