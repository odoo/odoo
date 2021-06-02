# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_sale_order_template = fields.Boolean("Quotation Templates", implied_group='sale_management.group_sale_order_template')
    default_sale_order_template_id = fields.Many2one('sale.order.template', default_model='sale.order', string='Default Template')
    module_sale_quotation_builder = fields.Boolean("Quotation Builder")

    @api.onchange('group_sale_order_template')
    def _onchange_group_sale_order_template(self):
        if not self.group_sale_order_template:
            self.module_sale_quotation_builder = False
            self.default_sale_order_template_id = False
