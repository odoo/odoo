# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import web, mail, auth_signup


class ResConfigSettings(web.ResConfigSettings, mail.ResConfigSettings, auth_signup.ResConfigSettings):

    portal_allow_api_keys = fields.Boolean(
        string='Customer API Keys',
        compute='_compute_portal_allow_api_keys',
        inverse='_inverse_portal_allow_api_keys',
    )

    def _compute_portal_allow_api_keys(self):
        for setting in self:
            setting.portal_allow_api_keys = self.env['ir.config_parameter'].sudo().get_param('portal.allow_api_keys')

    def _inverse_portal_allow_api_keys(self):
        self.env['ir.config_parameter'].sudo().set_param('portal.allow_api_keys', self.portal_allow_api_keys)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['portal_allow_api_keys'] = bool(self.env['ir.config_parameter'].sudo().get_param('portal.allow_api_keys'))
        return res
