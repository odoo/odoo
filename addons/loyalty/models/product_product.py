# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def write(self, vals):
        if not vals.get('active', True) and any(product.active for product in self):
            # Prevent archiving products used for giving rewards
            rewards = self.env['loyalty.reward'].sudo().search([('discount_line_product_id', 'in', self.ids)], limit=1)
            if rewards:
                raise ValidationError(_("This product may not be archived. It is being used for an active promotion program."))
        return super().write(vals)
