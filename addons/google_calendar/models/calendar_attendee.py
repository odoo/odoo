# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService

class Attendee(models.Model):
    _name = 'calendar.attendee'
    _inherit = 'calendar.attendee'

    def _send_mail_to_attendees(self, mail_template, force_send=False):
        """ Override
        If not synced with Google, let Odoo in charge of sending emails
        Otherwise, nothing to do: Google will send them
        """
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                super()._send_mail_to_attendees(mail_template, force_send)

    def do_tentative(self):
        # Synchronize event after state change
        res = super().do_tentative()
        self._sync_event()
        return res

    def do_accept(self):
        # Synchronize event after state change
        res = super().do_accept()
        self._sync_event()
        return res


    def do_decline(self):
        # Synchronize event after state change
        res = super().do_decline()
        self._sync_event()
        return res

    def _sync_event(self):
        # For weird reasons, we can't sync status when we are not the responsible
        # We can't adapt google_value to only keep ['id', 'summary', 'attendees', 'start', 'end', 'reminders']
        # and send that. We get a Forbidden for non-organizer error even if we only send start, end that are mandatory !
        if self._context.get('all_events'):
            service = GoogleCalendarService(self.env['google.service'].with_user(self.recurrence_id.base_event_id.user_id))
            self.recurrence_id.with_user(self.recurrence_id.base_event_id.user_id)._sync_odoo2google(service)
        else:
            all_events = self.mapped('event_id').filtered(lambda e: e.google_id)
            other_events = all_events.filtered(lambda e: e.user_id and e.user_id.id != self.env.user.id)
            for user in other_events.mapped('user_id'):
                service = GoogleCalendarService(self.env['google.service'].with_user(user))
                other_events.filtered(lambda ev: ev.user_id.id == user.id).with_user(user)._sync_odoo2google(service)
            google_service = GoogleCalendarService(self.env['google.service'])
            (all_events - other_events)._sync_odoo2google(google_service)
