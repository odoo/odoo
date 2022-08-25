# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.translate import html_translate


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    website_description = fields.Html(
        string="Website Description",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False)

    def action_open_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/sale_quotation_builder/template/%d' % self.id
        }
