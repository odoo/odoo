# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class CalendarConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    google_cal_sync = fields.Boolean(string="Show tutorial to know how to get my 'Client ID' and my 'Client Secret'")
    cal_client_id = fields.Char(string="Client_id")
    cal_client_secret = fields.Char(string="Client_key")
    server_uri = fields.Char(string="URI for tuto")

    @api.multi
    def set_calset(self):
        self.ensure_one()
        Params = self.env['ir.config_parameter']
        Params.set_param('google_calendar_client_id', (self.cal_client_id or '').strip(), groups=['base.group_system'])
        Params.set_param('google_calendar_client_secret', (self.cal_client_secret or '').strip(), groups=['base.group_system'])

    @api.model
    def get_default_all(self, fields):
        Params = self.env['ir.config_parameter']

        cal_client_id = Params.get_param('google_calendar_client_id', default='')
        cal_client_secret = Params.get_param('google_calendar_client_secret', default='')
        server_uri = "%s/google_account/authentication" % Params.get_param('web.base.url', default="http://yourcompany.odoo.com")
        return dict(cal_client_id=cal_client_id, cal_client_secret=cal_client_secret, server_uri=server_uri)
