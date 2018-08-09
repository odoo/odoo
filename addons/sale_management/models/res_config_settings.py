# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_quotation_template = fields.Boolean("Quotation Templates", implied_group='sale_management.group_quotation_template')
    default_template_id = fields.Many2one('sale.quote.template', default_model='sale.order', string='Default Template')
    module_sale_design = fields.Boolean("Quotation Builder")

    @api.onchange('group_quotation_template')
    def _onchange_group_quotation_template(self):
        if not self.group_quotation_template:
            self.module_sale_design = False
