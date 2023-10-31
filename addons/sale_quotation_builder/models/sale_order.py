# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_description = fields.Html('Website Description', sanitize_attributes=False, translate=html_translate, sanitize_form=False)

    @api.onchange('partner_id')
    def onchange_update_description_lang(self):
        if not self.sale_order_template_id:
            return
        else:
            template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
            self.website_description = template.website_description

    def _compute_line_data_for_template_change(self, line):
        vals = super(SaleOrder, self)._compute_line_data_for_template_change(line)
        vals.update(website_description=line.website_description)
        return vals

    def _compute_option_data_for_template_change(self, option):
        vals = super(SaleOrder, self)._compute_option_data_for_template_change(option)
        vals.update(website_description=option.website_description)
        return vals

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        ret = super(SaleOrder, self).onchange_sale_order_template_id()
        if self.sale_order_template_id:
            template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
            self.website_description = template.website_description
        return ret


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    website_description = fields.Html('Website Description', sanitize=False, translate=html_translate, sanitize_form=False)

    @api.model
    def create(self, values):
        values = self._inject_quotation_description(values)
        return super(SaleOrderLine, self).create(values)

    def write(self, values):
        values = self._inject_quotation_description(values)
        return super(SaleOrderLine, self).write(values)

    def _inject_quotation_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values.update(website_description=product.quotation_description)
        return values


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    website_description = fields.Html('Website Description', sanitize_attributes=False, translate=html_translate)

    @api.onchange('product_id', 'uom_id')
    def _onchange_product_id(self):
        ret = super(SaleOrderOption, self)._onchange_product_id()
        if self.product_id:
            product = self.product_id.with_context(lang=self.order_id.partner_id.lang)
            self.website_description = product.quotation_description
        return ret

    def _get_values_to_add_to_order(self):
        values = super(SaleOrderOption, self)._get_values_to_add_to_order()
        values.update(website_description=self.website_description)
        return values
