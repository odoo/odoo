# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_with_coupon_program(self):
        '''
        This methods prevents deleting Reward line product that is linked
        with Coupon/Promotion
        :return:
        '''
        coupon_prog_count = self.env['coupon.program'].sudo().with_context(active_test=False).search_count([('discount_line_product_id', 'in', self.ids)])
        if coupon_prog_count > 0:
            raise UserError(_("You cannot delete a product that is linked with Coupon or Promotion program. Archive it instead."))
