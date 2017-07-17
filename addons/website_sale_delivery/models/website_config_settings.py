# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    is_installed_easypost = fields.Boolean()

    @api.multi
    def get_default_is_installed_sale(self, fields):
        return {
            'is_installed_easypost': self.env['ir.module.module'].search([('name', '=', 'delivery_easypost'), ('state', '=', 'installed')]).id
        }
