# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class GoogleCalendarAccountReset(models.TransientModel):
    _name = 'google.calendar.account.reset'
    _description = 'Google Calendar Account Reset'

    user_id = fields.Many2one('res.users', required=True)
    delete_events = fields.Boolean(
        string="Delete synced events from Odoo",
        help="This will only affect events for which the user is the owner")

    def reset_account(self):
        if self.delete_events:
            events = self.env['calendar.event'].search([
                ('google_id', '!=', False),
                '|',
                    ('calendar_id', 'in', self.user_id.calendar_ids.ids),
                    ('user_id', '=', self.user_id.id)
                ])
            recurrences = self.env['calendar.recurrence'].search([
                ('base_event_id', 'in', events.ids),
                ('google_id', '!=', False)])

            # Clear google_id first. unlink() archives (instead of deleting) any event
            # still linked to Google, and archiving propagates the deletion to the remote
            # calendar. Detaching first lets us delete from Odoo only.
            events.with_context(skip_event_permission=True).google_id = False
            recurrences.with_context(skip_event_permission=True).google_id = False
            events.unlink()

        self.user_id.with_user(self.user_id).stop_google_synchronization()
