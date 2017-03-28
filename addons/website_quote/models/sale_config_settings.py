# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_template_id = fields.Many2one('sale.quote.template', string='Default Template')

    @api.multi
    def set_default_template_id(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'default_template_id', self.default_template_id.id)
