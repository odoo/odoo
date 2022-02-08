# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    website_description = fields.Html(
        string="Website Description",
        translate=html_translate,
        sanitize_attributes=False, sanitize_form=False)

    def open_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/sale_quotation_builder/template/%d' % self.id
        }


class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"

    # FIXME ANVFE why are the sanitize_* attributes different between this field
    # and the one on option lines, doesn't make any sense ???
    website_description = fields.Html(
        string="Website Description",
        compute='_compute_website_description',
        store=True, readonly=False,
        translate=html_translate,
        sanitize_form=False)

    @api.depends('product_id')
    def _compute_website_description(self):
        for line in self:
            if not line.product_id:
                continue
            line.website_description = line.product_id.quotation_description


class SaleOrderTemplateOption(models.Model):
    _inherit = "sale.order.template.option"

    website_description = fields.Html(
        string="Website Description",
        compute="_compute_website_description",
        store=True, readonly=False,
        translate=html_translate,
        sanitize_attributes=False)

    @api.depends('product_id')
    def _compute_website_description(self):
        for option in self:
            if not option.product_id:
                continue
            option.website_description = option.product_id.quotation_description
