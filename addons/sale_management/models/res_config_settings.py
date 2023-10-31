# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_sale_order_template = fields.Boolean(
        "Quotation Templates", implied_group='sale_management.group_sale_order_template')
    company_so_template_id = fields.Many2one(
        related="company_id.sale_order_template_id", string="Default Template", readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    module_sale_quotation_builder = fields.Boolean("Quotation Builder")

    @api.onchange('group_sale_order_template')
    def _onchange_group_sale_order_template(self):
        if not self.group_sale_order_template:
            self.module_sale_quotation_builder = False

    def set_values(self):
        if not self.group_sale_order_template:
            self.company_so_template_id = None
            self.env['res.company'].sudo().search([]).write({
                'sale_order_template_id': False,
            })
        return super(ResConfigSettings, self).set_values()
