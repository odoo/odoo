# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # we don't do a related on the product.template quote_description because in this case we want the description to be frozen
    website_description = fields.Html('Line Description', sanitize=False, translate=html_translate)

    @api.model
    def create(self, values):
        values = self._inject_quote_description(values)
        return super(SaleOrderLine, self).create(values)

    @api.multi
    def write(self, values):
        values = self._inject_quote_description(values)
        return super(SaleOrderLine, self).write(values)

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id']).with_context(lang=self.order_id.partner_id.lang)
            values['website_description'] = product.get_quote_description_or_website_description()
        return values


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_description = fields.Html('Description', sanitize_attributes=False, translate=html_translate)

    @api.onchange('partner_id')
    def onchange_update_description_lang(self):
        if not self.template_id:
            return
        else:
            template = self.template_id.with_context(lang=self.partner_id.lang)
            self.website_description = template.website_description

    @api.onchange('template_id')
    def onchange_template_id(self):
        res = super(SaleOrder, self).onchange_template_id()
        if self.template_id:
            template = self.template_id.with_context(lang=self.partner_id.lang)
            self.website_description = template.website_description
        return res


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    website_description = fields.Html('Line Description', sanitize_attributes=False, translate=html_translate)

    @api.onchange('product_id', 'uom_id')
    def _onchange_product_id(self):
        res = super(SaleOrderOption, self)._onchange_product_id()
        if self.product_id:
            product = self.product_id.with_context(lang=self.order_id.partner_id.lang)
            self.website_description = product.get_quote_description_or_website_description()
        return res

    def _get_vals_add_to_order(self):
        vals = super(SaleOrderOption, self)._get_vals_add_to_order()
        vals.update(website_description=self.website_description)
        return vals
