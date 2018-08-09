# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleQuoteTemplate(models.Model):
    _inherit = "sale.quote.template"

    website_description = fields.Html('Description', translate=html_translate, sanitize_attributes=False)

    @api.multi
    def open_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quotation/template/%d' % self.id
        }


class SaleQuoteLine(models.Model):
    _inherit = "sale.quote.line"

    website_description = fields.Html('Line Description', related='product_id.product_tmpl_id.quote_description', translate=html_translate)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        ret = super(SaleQuoteLine, self)._onchange_product_id()
        if self.product_id:
            self.website_description = self.product_id.get_quote_description_or_website_description()
        return ret

    @api.model
    def create(self, values):
        values = self._inject_quote_description(values)
        return super(SaleQuoteLine, self).create(values)

    @api.multi
    def write(self, values):
        values = self._inject_quote_description(values)
        return super(SaleQuoteLine, self).write(values)

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.get_quote_description_or_website_description()
        return values


class SaleQuoteOption(models.Model):
    _inherit = "sale.quote.option"

    website_description = fields.Html('Option Description', translate=html_translate, sanitize_attributes=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        ret = super(SaleQuoteOption, self)._onchange_product_id()
        if self.product_id:
            self.website_description = self.product_id.get_quote_description_or_website_description()
        return ret
