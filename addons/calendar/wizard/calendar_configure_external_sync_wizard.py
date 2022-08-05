# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.models.ir_module import assert_log_admin_access
from odoo import _, fields, models, api


class CalendarConfigureExternalSyncWizard(models.TransientModel):
    _name = 'calendar.configure.external.sync.wizard'
    _description = 'Configure and sync external calendar Wizard'

    external_calendar_provider = fields.Selection([
        ('google', 'Google'), ('microsoft', 'Outlook')],
        _("Choose an external calendar to configure"),
        default=lambda self: 'microsoft' if self.env['ir.config_parameter'].sudo().get_param('microsoft_calendar_client_id') else 'google')

    # Allow to sync with eventually existing ICP keys without creating them if respective module is not installed
    cal_google_client_id = fields.Char(
        "Google Client_id",
        default=lambda self: self.env['ir.config_parameter'].get_param('google_calendar_client_id'))
    cal_google_client_secret = fields.Char(
        "Google Client_key",
        default=lambda self: self.env['ir.config_parameter'].get_param('google_calendar_client_secret'))
    cal_microsoft_client_id = fields.Char(
        "Microsoft Client_id",
        default=lambda self: self.env['ir.config_parameter'].get_param('microsoft_calendar_client_id'))
    cal_microsoft_client_secret = fields.Char(
        "Microsoft Client_key",
        default=lambda self: self.env['ir.config_parameter'].get_param('microsoft_calendar_client_secret'))

    @assert_log_admin_access
    @api.model
    def action_configure_with_optional_install(self, values):
        calendar_provider = values["external_calendar_provider"]
        calendar_module = self.env['ir.module.module'].search([('name', '=', f'{calendar_provider}_calendar')])
        if calendar_module.state != 'installed':
            calendar_module.button_immediate_install()

        self.env['ir.config_parameter'].set_param(
            f'{calendar_provider}_calendar_client_id', values[f'cal_{calendar_provider}_client_id'])
        self.env['ir.config_parameter'].set_param(
            f'{calendar_provider}_calendar_client_secret', values[f'cal_{calendar_provider}_client_secret'])
