# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.tools import str2bool


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    connector_google = fields.Boolean(compute="_compute_connector_google")
    event_videocall_source = fields.Selection(selection_add=[('google_meet', 'Google Meet')], ondelete={'google_meet': 'set default'})
    users_wo_google_calendar_msg = fields.Html('Users Without Google Calendar Synchronization',
        compute='_compute_users_wo_google_calendar_msg')

    @api.depends('staff_user_ids', 'event_videocall_source')
    def _compute_users_wo_google_calendar_msg(self):
        self.users_wo_google_calendar_msg = False
        for appointment_type in self.filtered(lambda apt: apt.event_videocall_source == 'google_meet'):
            users_not_synchronized = appointment_type.staff_user_ids.filtered(
                lambda user: not user.is_google_calendar_synced())
            if users_not_synchronized:
                appointment_type.users_wo_google_calendar_msg = _(
                    '%(user_names)s did not synchronize their Google Calendar account yet, Google Meeting links won\'t be added to their meetings.',
                    user_names=Markup(', ').join(Markup('<b>%s</b>') % user.name for user in users_not_synchronized))
            if not self.connector_google:
                appointment_type.users_wo_google_calendar_msg = _('Google Sync is either paused or not properly configured. Google Meet links won\'t be added to the meetings.')

    def _compute_connector_google(self):
        self.connector_google = "google" in self._get_calendars_possible_to_setup()

    def _get_calendars_already_setup(self):
        calendars = super()._get_calendars_already_setup()
        if self.env.user.sudo().google_calendar_token:
            calendars.append("google")
        return calendars

    def _get_calendars_possible_to_setup(self):
        calendars = super()._get_calendars_possible_to_setup()
        if (self.env['google.service']._get_client_id('calendar') and
            not str2bool(self.env['ir.config_parameter'].sudo().get_param("google_calendar_sync_paused"))):
            calendars.append("google")
        return calendars
