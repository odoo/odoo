import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

class MicrosoftCredentials(models.Model):
    """"Microsoft Account of res_users"""

    _name = 'microsoft.calendar.credentials'
    _description = 'Microsoft Calendar Account Data'

    user_ids = fields.One2many('res.users', 'microsoft_calendar_account_id', required=True)
    calendar_sync_token = fields.Char('Microsoft Next Sync Token', copy=False)
    synchronization_stopped = fields.Boolean('Outlook Synchronization stopped', copy=False)
    last_sync_date = fields.Datetime('Last Sync Date', copy=False, help='Last synchronization date with Outlook Calendar')
