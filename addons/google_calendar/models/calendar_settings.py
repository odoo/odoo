# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarSettings(models.Model):
    _inherit = "calendar.settings"

    # Google Calendar tokens and synchronization information.
    google_calendar_sync_token = fields.Char('Next Sync Token', copy=False, groups='base.group_system')
    google_calendar_cal_id = fields.Char('Calendar ID', copy=False, groups='base.group_system',
        help='Last Calendar ID who has been synchronized. If it is changed, we remove all links between GoogleID and Odoo Google Internal ID')

    @api.model
    def _get_fields_blacklist(self):
        """ Get list of google fields that won't be formatted in session_info. """
        google_fields_blacklist = [
            'google_calendar_sync_token',
            'google_calendar_cal_id',
        ]
        return super()._get_fields_blacklist() + google_fields_blacklist
