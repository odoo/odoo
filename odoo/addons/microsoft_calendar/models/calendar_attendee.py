# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService


class Attendee(models.Model):
    _name = 'calendar.attendee'
    _inherit = 'calendar.attendee'

    def _send_mail_to_attendees(self, mail_template, force_send=False):
        """ Override the super method
        If not synced with Microsoft Outlook, let Odoo in charge of sending emails
        Otherwise, Microsoft Outlook will send them
        """
        with microsoft_calendar_token(self.env.user.sudo()) as token:
            if not token:
                super()._send_mail_to_attendees(mail_template, force_send)

    def do_tentative(self):
        # Synchronize event after state change
        res = super().do_tentative()
        self._microsoft_sync_event('tentativelyAccept')
        return res

    def do_accept(self):
        # Synchronize event after state change
        res = super().do_accept()
        self._microsoft_sync_event('accept')
        return res


    def do_decline(self):
        # Synchronize event after state change
        res = super().do_decline()
        self._microsoft_sync_event('decline')
        return res

    def _microsoft_sync_event(self, answer):
        params = {"comment": "", "sendResponse": True}
        # Microsoft prevent user to answer the meeting when they are the organizer
        linked_events = self.event_id._get_synced_events()
        for event in linked_events:
            if event._check_microsoft_sync_status() and self.env.user != event.user_id and self.env.user.partner_id in event.partner_ids:
                if event.recurrency:
                    event._forbid_recurrence_update()
                event._microsoft_attendee_answer(answer, params)
