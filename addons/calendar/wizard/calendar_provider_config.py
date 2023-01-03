# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.base.models.ir_module import assert_log_admin_access


class CalendarProviderConfig(models.TransientModel):
    _name = 'calendar.provider.config'
    _description = 'Calendar Provider Configuration Wizard'

    external_calendar_provider = fields.Selection([
        ('google', 'Google'), ('microsoft', 'Outlook')],
        "Choose an external calendar to configure", default='google')

    # Allow to sync with eventually existing ICP keys without creating them if respective module is not installed
    # Using same field names and strings as their respective res.config.settings
    cal_client_id = fields.Char(
        "Google Client_id",
        default=lambda self: self.env['ir.config_parameter'].get_param('google_calendar_client_id'))
    cal_client_secret = fields.Char(
        "Google Client_key",
        default=lambda self: self.env['ir.config_parameter'].get_param('google_calendar_client_secret'))
    microsoft_outlook_client_identifier = fields.Char(
        "Outlook Client Id",
        default=lambda self: self.env['ir.config_parameter'].get_param('microsoft_calendar_client_id'))
    microsoft_outlook_client_secret = fields.Char(
        "Outlook Client Secret",
        default=lambda self: self.env['ir.config_parameter'].get_param('microsoft_calendar_client_secret'))

    @assert_log_admin_access
    def action_calendar_prepare_external_provider_sync(self):
        """ Called by the wizard to configure an external calendar provider without requiring users
        to access the general settings page.
        Make sure that the provider calendar module is installed or install it. Then, set
        the API keys into the applicable config parameters.
        """
        self.ensure_one()
        calendar_module = self.env['ir.module.module'].search([
            ('name', '=', f'{self.external_calendar_provider}_calendar')])

        if calendar_module.state != 'installed':
            calendar_module.button_immediate_install()

        if self.external_calendar_provider == 'google':
            self.env['ir.config_parameter'].set_param('google_calendar_client_id', self.cal_client_id)
            self.env['ir.config_parameter'].set_param('google_calendar_client_secret', self.cal_client_secret)
        elif self.external_calendar_provider == 'microsoft':
            self.env['ir.config_parameter'].set_param('microsoft_calendar_client_id', self.microsoft_outlook_client_identifier)
            self.env['ir.config_parameter'].set_param('microsoft_calendar_client_secret', self.microsoft_outlook_client_secret)
