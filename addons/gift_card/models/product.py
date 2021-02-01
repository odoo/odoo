# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_gift_card = fields.Boolean(default=False, help="This product is converted into a gift card when purchased.")

    @api.ondelete(at_uninstall=False)
    def _unlink_gift_card_product(self):
        if self.env.ref('gift_card.pay_with_gift_card_product').product_tmpl_id in self:
            raise UserError(_('Deleting the Gift Card Pay product is not allowed.'))
