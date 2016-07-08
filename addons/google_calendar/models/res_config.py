# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarSettings(models.TransientModel):

    _inherit = 'base.config.settings'

    google_cal_sync = fields.Boolean("Show Tutorial")
    cal_client_id = fields.Char("Client_id")
    cal_client_secret = fields.Char("Client_key")
    server_uri = fields.Char('URI for tuto')

    def set_calset(self):
        self.env['ir.config_parameter'].set_param('google_calendar_client_id', (self.cal_client_id or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('google_calendar_client_secret', (self.cal_client_secret or '').strip(), groups=['base.group_system'])

    def get_default_all(self, fields):
        cal_client_id = self.env['ir.config_parameter'].get_param('google_calendar_client_id', default='')
        cal_client_secret = self.env['ir.config_parameter'].get_param('google_calendar_client_secret', default='')
        server_uri = "%s/google_account/authentication" % self.env['ir.config_parameter'].get_param('web.base.url', default="http://yourcompany.odoo.com")
        return dict(cal_client_id=cal_client_id, cal_client_secret=cal_client_secret, server_uri=server_uri)
