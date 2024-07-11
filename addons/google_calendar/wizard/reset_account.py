# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class ResetGoogleAccount(models.TransientModel):
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
        google = GoogleCalendarService(self.env['google.service'])

        events = self.env['calendar.event'].search([
            ('user_id', '=', self.user_id.id),
            ('google_id', '!=', False)])
        if self.delete_policy in ('delete_google', 'delete_both'):
            with google_calendar_token(self.user_id) as token:
                for event in events:
                    google.delete(event.google_id, token=token)

        if self.delete_policy in ('delete_odoo', 'delete_both'):
            events.google_id = False
            events.unlink()

        if self.sync_policy == 'all':
            events.write({
                'google_id': False,
                'need_sync': True,
            })

        self.user_id.google_calendar_account_id._set_auth_tokens(False, False, 0)
        self.user_id.write({
            'google_calendar_sync_token': False,
            'google_calendar_cal_id': False,
        })
