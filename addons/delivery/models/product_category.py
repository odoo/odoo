# -*- coding: utf-8 -*-
from odoo.addons import product
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class ProductCategory(models.Model, product.ProductCategory):

    @api.ondelete(at_uninstall=False)
    def _unlink_except_delivery_category(self):
        delivery_category = self.env.ref('delivery.product_category_deliveries', raise_if_not_found=False)
        if delivery_category and delivery_category in self:
            raise UserError(_("You cannot delete the deliveries product category as it is used on the delivery carriers products."))
