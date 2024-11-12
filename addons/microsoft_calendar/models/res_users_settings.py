# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    # Microsoft Calendar settings.
    microsoft_calendar_sync_token = fields.Char('Microsoft Next Sync Token', copy=False, groups='base.group_system')
    microsoft_synchronization_stopped = fields.Boolean('Outlook Synchronization stopped', copy=False, groups='base.group_system')
    microsoft_last_sync_date = fields.Datetime('Last Sync Date', copy=False, help='Last synchronization date with Outlook Calendar', groups='base.group_system')

    @api.model
    def _get_fields_blacklist(self):
        """ Get list of microsoft fields that won't be formatted in session_info. """
        microsoft_fields_blacklist = [
            'microsoft_calendar_sync_token',
            'microsoft_synchronization_stopped',
            'microsoft_last_sync_date',
        ]
        return super()._get_fields_blacklist() + microsoft_fields_blacklist
