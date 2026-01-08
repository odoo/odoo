# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_sale_order_template = fields.Boolean(
        "Quotation Templates", implied_group='sale_management.group_sale_order_template')
    company_so_template_id = fields.Many2one(
        related="company_id.sale_order_template_id", string="Default Template", readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def set_values(self):
        if not self.group_sale_order_template:
            if self.company_so_template_id:
                self.company_so_template_id = False
            companies = self.env['res.company'].sudo().search([
                ('sale_order_template_id', '!=', False)
            ])
            if companies:
                companies.sale_order_template_id = False
        super().set_values()
