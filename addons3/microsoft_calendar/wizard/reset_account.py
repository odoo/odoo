# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token


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
        # We don't update recurring events to prevent spam
        events = self.env['calendar.event'].search([
            ('user_id', '=', self.user_id.id),
            ('ms_universal_event_id', '!=', False)])
        non_recurring_events = self.env['calendar.event'].search([
            ('user_id', '=', self.user_id.id),
            ('recurrence_id', '=', False),
            ('ms_universal_event_id', '!=', False)])

        if self.delete_policy in ('delete_microsoft', 'delete_both'):
            for event in non_recurring_events:
                event._microsoft_delete(event._get_organizer(), event.ms_organizer_event_id, timeout=3)

        if self.sync_policy == 'all':
            events.with_context(dont_notify=True).update({
                'microsoft_id': False,
                'need_sync_m': True,
            })

        if self.delete_policy in ('delete_odoo', 'delete_both'):
            events.with_context(dont_notify=True).microsoft_id = False
            events.unlink()

        # We commit to make sure the _microsoft_delete are called when we still have a token on the user.
        self.env.cr.commit()
        self.user_id._set_microsoft_auth_tokens(False, False, 0)
        self.user_id.microsoft_calendar_account_id.write({
            'calendar_sync_token': False,
            'last_sync_date': False
        })
