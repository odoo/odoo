# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleCoupon(models.Model):
    _inherit = 'coupon.coupon'

<<<<<<< HEAD
    def _check_coupon_code(self, order):
        if self.program_id.website_id and self.program_id.website_id != order.website_id:
            return {'error': 'This coupon is not valid on this website.'}
        return super()._check_coupon_code(order)
=======
    def _check_coupon_code(self, order_date, partner_id, **kwargs):
        order = kwargs.get('order', False)
        if order and self.program_id.website_id and self.program_id.website_id != order.website_id:
            return {'error': 'This coupon is not valid on this website.'}
        return super()._check_coupon_code(order_date, partner_id, **kwargs)
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
