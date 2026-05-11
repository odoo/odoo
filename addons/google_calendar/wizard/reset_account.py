# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class GoogleCalendarAccountReset(models.TransientModel):
    _name = 'google.calendar.account.reset'
    _description = 'Google Calendar Account Reset'

    user_id = fields.Many2one('res.users', required=True)
    delete_policy = fields.Selection(
        [('dont_delete', "Leave them untouched"),
         ('delete_google', "Delete from the current Google Calendar account"),
         ('delete_odoo', "Delete from Odoo"),
         ('delete_both', "Delete from both"),
        ], string="User's Existing Events", required=True, default='dont_delete',
        help="This will only affect events for which the user is the owner")
    sync_policy = fields.Selection([
        ('new', "Synchronize only new events"),
        ('all', "Synchronize all existing events"),
    ], string="Next Synchronization", required=True, default='new')

    def reset_account(self):
        events = self.env['calendar.event'].search([
            ('user_id', '=', self.user_id.id),
            ('google_id', '!=', False)])
        recurrences = self.env['calendar.recurrence'].search([
            ('base_event_id', 'in', events.ids),
            ('google_id', '!=', False)])

        google_ids_to_delete = []
        if self.delete_policy in ('delete_google', 'delete_both'):
            # Queue delete requests only for standalone events and recurrence masters.
            # Because Google automatically deletes all child instances when a master is deleted,
            # queuing individual instances is redundant and could exceed the 600 req/min API quota.
            standalone_events = events.filtered(lambda e: e.recurrence_id not in recurrences)
            google_ids_to_delete = recurrences.mapped('google_id') + standalone_events.mapped('google_id')

            if google_ids_to_delete:
                self.env['google.calendar.pending.deletion'].sudo().create([
                    {'google_id': google_id, 'user_id': self.user_id.id}
                    for google_id in google_ids_to_delete
                ])
                self.env.ref('google_calendar.ir_cron_process_google_pending_deletions')._trigger()

        # Delete events according to the selected policy. If the deletion is only in
        # Google, we won't keep track of the 'google_id' field for events and recurrences.
        if self.delete_policy in ('delete_odoo', 'delete_both', 'delete_google'):
            # Flag need_sync as False in order to skip the write permission when resetting.
            events.with_context(skip_event_permission=True).google_id = False
            recurrences.with_context(skip_event_permission=True).google_id = False
            if self.delete_policy != 'delete_google':
                events.unlink()

        # Define which events must be synchronized in the next synchronization:
        # in 'all' sync policy we activate the sync for all events and in the 'new'
        # sync policy we set it as False for skipping existing events synchronization.
        next_sync_update = {}
        if self.sync_policy == 'all':
            next_sync_update['need_sync'] = True
        elif self.sync_policy == 'new':
            next_sync_update['need_sync'] = False

        # Write the next sync update attribute on the existing events.
        if self.delete_policy not in ('delete_odoo', 'delete_both'):
            events.with_context(skip_event_permission=True).write(next_sync_update)

        if google_ids_to_delete:
            # Credentials must stay valid until the cron has processed the
            # queue on Google's side. Re-linking will be blocked in the meantime.
            self.user_id.res_users_settings_id.sudo().google_calendar_reset_pending = True
        else:
            self.user_id.res_users_settings_id._finalize_google_calendar_reset()
