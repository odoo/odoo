# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class JournalConfig(models.TransientModel):
    _inherit = ['res.config.settings']

    notice_period = fields.Boolean(string='Notice Period')
    no_of_days = fields.Integer()

    def set_values(self):
        super(JournalConfig, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            "hr_resignation.notice_period", self.notice_period)
        self.env['ir.config_parameter'].sudo().set_param(
            "hr_resignation.no_of_days", self.no_of_days)

    @api.model
    def get_values(self):
        res = super(JournalConfig, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res['notice_period'] = get_param('hr_resignation.notice_period')
        res['no_of_days'] = int(get_param('hr_resignation.no_of_days'))
        return res
