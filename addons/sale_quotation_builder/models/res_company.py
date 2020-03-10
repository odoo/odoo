# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _set_default_sale_order_template_id_if_empty(self):
        template = self.env.ref('sale_quotation_builder.sale_order_template_default', raise_if_not_found=False)
        if not template:
            return
        companies = self.sudo().search([])
        for company in companies:
            company.sale_order_template_id = company.sale_order_template_id or template
