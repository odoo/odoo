# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    website_description = fields.Html('Website Description', translate=html_translate, sanitize_attributes=False)

    def open_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/sale_quotation_builder/template/%d' % self.id
        }


class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"

    website_description = fields.Html('Website Description', related='product_id.product_tmpl_id.quotation_only_description', translate=html_translate, readonly=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        ret = super(SaleOrderTemplateLine, self)._onchange_product_id()
        if self.product_id:
            self.website_description = self.product_id.quotation_description
        return ret

    @api.model
    def create(self, values):
        values = self._inject_quotation_description(values)
        return super(SaleOrderTemplateLine, self).create(values)

    def write(self, values):
        values = self._inject_quotation_description(values)
        return super(SaleOrderTemplateLine, self).write(values)

    def _inject_quotation_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.quotation_description
        return values


class SaleOrderTemplateOption(models.Model):
    _inherit = "sale.order.template.option"

    website_description = fields.Html('Website Description', translate=html_translate, sanitize_attributes=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        ret = super(SaleOrderTemplateOption, self)._onchange_product_id()
        if self.product_id:
            self.website_description = self.product_id.quotation_description
        return ret
