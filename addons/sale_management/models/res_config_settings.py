# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_quotation_template = fields.Boolean("Quotations Templates", implied_group='sale_management.group_quotation_template')
    default_template_id = fields.Many2one('sale.quote.template', default_model='sale.order', string='Default Template')
