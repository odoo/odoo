# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import str2bool


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    connector_microsoft = fields.Boolean(compute="_compute_connector_microsoft")

    def _compute_connector_microsoft(self):
        self.connector_microsoft = "microsoft" in self._get_calendars_possible_to_setup()

    def _get_calendars_already_setup(self):
        calendars = super()._get_calendars_already_setup()
        if self.env.user.sudo().microsoft_calendar_token:
            calendars.append("microsoft")
        return calendars

    def _get_calendars_possible_to_setup(self):
        calendars = super()._get_calendars_possible_to_setup()
        if (self.env.user.check_synchronization_status()['microsoft_calendar'] != 'missing_credentials' and
            not str2bool(self.env['ir.config_parameter'].sudo().get_param("microsoft_calendar_sync_paused"))):
            calendars.append("microsoft")
        return calendars
