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

            # Clear microsoft_id first. unlink() deletes any still-linked event from the
            # remote Outlook calendar. Detaching first lets us delete from Odoo only.
            events.with_context(dont_notify=True).microsoft_id = False
            events.unlink()

        self.user_id.with_user(self.user_id).stop_microsoft_synchronization()
