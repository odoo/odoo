# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_description = fields.Html('Website Description', sanitize_attributes=False, translate=html_translate, sanitize_form=False,
                                      compute='_compute_website_description')

    def _compute_website_description(self):
        for r in self:
            r.website_description = r.sale_order_template_id.with_context(lang=self.env.lang).website_description


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    website_description = fields.Html('Website Description', sanitize=False, translate=html_translate, sanitize_form=False,
                                      compute='_compute_website_description')

    def _compute_website_description(self):
        for r in self:
            r.website_description = r.product_id.with_context(lang=self.env.lang).quotation_description


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    website_description = fields.Html('Website Description', sanitize_attributes=False, translate=html_translate)

    def _compute_website_description(self):
        for r in self:
            r.website_description = r.product_id.with_context(lang=self.env.lang).quotation_description
