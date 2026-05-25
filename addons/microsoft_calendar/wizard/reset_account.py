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
        events = self.env['calendar.event'].search([
            ('user_id', '=', self.user_id.id),
            ('ms_universal_event_id', '!=', False)])

        if self.delete_events:
            # Clear microsoft_id first. unlink() deletes any still-linked event from the
            # remote Outlook calendar. Detaching first lets us delete from Odoo only.
            events.with_context(dont_notify=True).microsoft_id = False
            events.unlink()

        self.user_id._set_microsoft_auth_tokens(False, False, 0)
        self.user_id.res_users_settings_id.write({
            'microsoft_calendar_sync_token': False,
            'microsoft_last_sync_date': False
        })
