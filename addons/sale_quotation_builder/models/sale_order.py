# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_description = fields.Html(
        'Website Description', sanitize_attributes=False, sanitize_form=False,
        compute="_compute_website_description", store=True, copy=True, readonly=False)

    @api.depends("sale_order_template_id", "partner_id")
    def _compute_website_description(self):
        for order in self:
            order.website_description = order.with_context(
                lang=order.partner_id.lang
            ).sale_order_template_id.website_description


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    website_description = fields.Html(
        'Website Description', sanitize=False, readonly=False, sanitize_form=False,
        compute="_compute_website_description", store=True, copy=True,
    )

    @api.depends('product_id')
    def _compute_website_description(self):
        for line in self:
            line.website_description = line.with_context(
                lang=line.order_partner_id.lang
            ).product_id.quotation_description


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    # VFE TODO isn't there a missing sanitize_form=False here ???
    website_description = fields.Html(
        'Website Description', sanitize=False, readonly=False,
        compute="_compute_website_description", store=True, copy=True,
    )

    @api.depends('product_id')
    def _compute_website_description(self):
        for option in self:
            option.website_description = option.with_context(
                lang=option.order_id.partner_id.lang
            ).product_id.quotation_description

    def _get_values_to_add_to_order(self):
        values = super(SaleOrderOption, self)._get_values_to_add_to_order()
        values.update(website_description=self.website_description)
        return values
