# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def unlink(self):
        '''
        This methods prevents deleting Reward line product that is linked
        with Coupon/Promotion
        :return:
        '''
        coupon_prog = self.env['coupon.program'].with_context(active_test=False).search_count([('discount_line_product_id','in', (self.ids))])
        if coupon_prog > 0:
            raise ValidationError(_("You cannot delete the product(s)\
                    that is linked with Coupon or Promotion program, Archive instead."))
        return super(ProductProduct,self).unlink()

