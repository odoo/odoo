from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    # Microsoft Calendar settings.
    microsoft_calendar_sync_token = fields.Char(
        string="Microsoft Next Sync Token",
        copy=False,
        groups="base.group_system",
    )
    microsoft_synchronization_stopped = fields.Boolean(
        string="Outlook Synchronization stopped",
        copy=False,
        groups="base.group_system",
    )
    microsoft_last_sync_date = fields.Datetime(
        string="Last Sync Date",
        copy=False,
        groups="base.group_system",
        help="Last synchronization date with Outlook Calendar",
    )

    @api.model
    def _get_fields_blacklist(self):
        """Get list of microsoft fields that won't be formatted in session_info."""
        microsoft_fields_blacklist = [
            "microsoft_calendar_sync_token",
            "microsoft_synchronization_stopped",
            "microsoft_last_sync_date",
        ]
        return super()._get_fields_blacklist() + microsoft_fields_blacklist
