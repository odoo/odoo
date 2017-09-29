# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cal_client_id = fields.Char("Client_id")
    cal_client_secret = fields.Char("Client_key")
    server_uri = fields.Char('URI for tuto')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].set_param
        set_param('google_calendar_client_id', (self.cal_client_id or '').strip())
        set_param('google_calendar_client_secret', (self.cal_client_secret or '').strip())

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            cal_client_id=get_param('google_calendar_client_id', default=''),
            cal_client_secret=get_param('google_calendar_client_secret', default=''),
            server_uri="%s/google_account/authentication" % get_param('web.base.url', default="http://yourcompany.odoo.com"),
        )
        return res
