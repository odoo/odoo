# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MicrosoftCalendarAccountReset(models.TransientModel):
    _name = 'microsoft.calendar.account.reset'
    _description = 'Microsoft Calendar Account Reset'

    user_id = fields.Many2one('res.users', required=True)
    delete_events = fields.Boolean(
        string="Delete synced events from Odoo",
        help="This will only affect events for which the user is the owner")

    def reset_account(self):
        if self.delete_events:
            events = self.env['calendar.event'].search([
                ('user_id', '=', self.user_id.id),
                ('ms_universal_event_id', '!=', False)])

<<<<<<< 76a0310536114e776bc46ca70af7f4b42284f073
            # Clear microsoft_id first. unlink() deletes any still-linked event from the
            # remote Outlook calendar. Detaching first lets us delete from Odoo only.
            events.with_context(dont_notify=True).microsoft_id = False
||||||| b558aea35c3437e63dc8479627cc75c23220b553
        if self.delete_policy in ('delete_microsoft', 'delete_both'):
            for event in non_recurring_events:
                event._microsoft_delete(event._get_organizer(), event.microsoft_id, timeout=3)

        if self.sync_policy == 'all':
            events.with_context(dont_notify=True).update({
                'microsoft_id': False,
                'need_sync_m': True,
            })

        if self.delete_policy in ('delete_odoo', 'delete_both'):
            events.with_context(dont_notify=True).microsoft_id = False
=======
        if self.delete_policy in ('delete_microsoft', 'delete_both'):
            for event in non_recurring_events:
                event._microsoft_delete(event._get_organizer(), event.microsoft_id, timeout=3)

        if self.sync_policy == 'all':
            events.with_context(dont_notify=True).update({
                'microsoft_id': False,
                'ms_universal_event_id': False,
                'need_sync_m': True,
            })

        if self.delete_policy in ('delete_odoo', 'delete_both'):
            events.with_context(dont_notify=True).write({
                'microsoft_id': False,
                'ms_universal_event_id': False,
            })
>>>>>>> 304c78f684cb3f3a5395cd7feac1629ac3b7d6d5
            events.unlink()

        self.user_id.with_user(self.user_id).stop_microsoft_synchronization()
