# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_description = fields.Html(
        'Website Description', sanitize_attributes=False, translate=html_translate, sanitize_form=False,
        compute='_compute_website_description', store=True, readonly=False)

    @api.depends('partner_id', 'sale_order_template_id')
    def _compute_website_description(self):
        for order in self:
            if not order.sale_order_template_id:
                continue
            template = order.sale_order_template_id.with_context(lang=order.partner_id.lang)
            order.website_description = template.website_description

    def _compute_line_data_for_template_change(self, line):
        vals = super(SaleOrder, self)._compute_line_data_for_template_change(line)
        vals.update(website_description=line.website_description)
        return vals

    def _compute_option_data_for_template_change(self, option):
        vals = super(SaleOrder, self)._compute_option_data_for_template_change(option)
        vals.update(website_description=option.website_description)
        return vals
