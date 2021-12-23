# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    website_description = fields.Html('Website Description', sanitize=False, translate=html_translate, sanitize_form=False)

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._inject_quotation_description(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, values):
        values = self._inject_quotation_description(values)
        return super().write(values)

    def _inject_quotation_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values.update(website_description=product.quotation_description)
        return values
