# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleQuoteTemplate(models.Model):
    _inherit = "sale.quote.template"

    website_description = fields.Html('Description', translate=html_translate, sanitize_attributes=False)


class SaleQuoteLine(models.Model):
    _inherit = "sale.quote.line"

    # this website_description is related because we want to update the product.template quote_description
    # when we update the quote.line website_description with the website editor
    website_description = fields.Html('Line Description', related='product_id.product_tmpl_id.quote_description',
        translate=html_translate)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.ensure_one()
        if self.product_id:
            self.website_description = self.product_id.get_quote_description_or_website_description()
        return super(SaleQuoteLine, self)._onchange_product_id()

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
            values.update(website_description=product.get_quote_description_or_website_description())
        return values

    def _get_vals_to_apply_template(self):
        vals = super(SaleQuoteLine, self)._get_vals_to_apply_template()
        vals.update(website_description=self.website_description)
        return vals


class SaleQuoteOption(models.Model):
    _inherit = "sale.quote.option"

    # why for options we don't modify the one from the product?
    website_description = fields.Html('Option Description', translate=html_translate, sanitize_attributes=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.website_description = self.product_id.get_quote_description_or_website_description()
        return super(SaleQuoteOption, self)._onchange_product_id()

    def _get_vals_to_apply_template(self):
        vals = super(SaleQuoteOption, self)._get_vals_to_apply_template()
        vals.update(website_description=self.website_description)
        return vals
