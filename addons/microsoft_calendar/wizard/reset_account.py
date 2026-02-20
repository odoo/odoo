# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token


class MicrosoftCalendarAccountReset(models.TransientModel):
    _name = 'microsoft.calendar.account.reset'
    _description = 'Microsoft Calendar Account Reset'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    delete_policy = fields.Selection(
        [('dont_delete', "Leave them untouched"),
         ('delete_odoo', "Delete from Odoo"),
    ], string="User's Existing Events", required=True, default='dont_delete',
    help="This will only affect events for which the user is the owner")

    def reset_account(self):
        if self.delete_policy == 'delete_odoo':
            events = self.env['calendar.event'].search([
                ('user_id', '=', self.user_id.id),
                ('ms_universal_event_id', '!=', False)])
            events.with_context(dont_notify=True).microsoft_id = False
            events.unlink()

        self.user_id._set_microsoft_auth_tokens(False, False, 0)
        self.user_id.res_users_settings_id.write({
            'microsoft_calendar_sync_token': False,
            'microsoft_last_sync_date': False
        })
