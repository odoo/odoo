# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService


class ResetMicrosoftAccount(models.TransientModel):
    _name = 'microsoft.calendar.account.reset'
    _description = 'Microsoft Calendar Account Reset'

    user_id = fields.Many2one('res.users', required=True)
    delete_policy = fields.Selection(
        [('dont_delete', "Leave them untouched"),
         ('delete_microsoft', "Delete from the current Microsoft Calendar account"),
         ('delete_odoo', "Delete from Odoo"),
         ('delete_both', "Delete from both"),
    ], string="User's Existing Events", required=True, default='dont_delete',
    help="This will only affect events for which the user is the owner")
    sync_policy = fields.Selection([
        ('new', "Synchronize only new events"),
        ('all', "Synchronize all existing events"),
    ], string="Next Synchronization", required=True, default='new')

    def reset_account(self):
        microsoft = MicrosoftCalendarService(self.env['microsoft.service'])

        events = self.env['calendar.event'].search([
            ('user_id', '=', self.user_id.id),
            ('microsoft_id', '!=', False)])
        if self.delete_policy in ('delete_microsoft', 'delete_both'):
            with microsoft_calendar_token(self.user_id) as token:
                for event in events:
                    microsoft.delete(event.microsoft_id, token=token)

        if self.delete_policy in ('delete_odoo', 'delete_both'):
            events.microsoft_id = False
            events.unlink()

        if self.sync_policy == 'all':
            events.write({
                'microsoft_id': False,
                'need_sync_m': True,
            })

        self.user_id._set_microsoft_auth_tokens(False, False, 0)
        self.user_id.write({
            'microsoft_calendar_sync_token': False,
        })
