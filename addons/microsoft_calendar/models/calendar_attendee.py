# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService


class Attendee(models.Model):
    _name = 'calendar.attendee'
    _inherit = 'calendar.attendee'

    def write(self, vals):
        """
            Tell to resync the link microsoft/odoo of the event when the status of an attendee is modified
        """
        res = super().write(vals)
        if vals.get('state'):
            # When the state is changed, the corresponding event must be sync with microsoft
            microsoft_service = MicrosoftCalendarService(self.env['microsoft.service'])
            self.event_id.filtered('microsoft_id')._sync_odoo2microsoft(microsoft_service)
        return res

    def _send_mail_to_attendees(self, mail_template, force_send=False):
        """ Override the super method
        If not synced with Microsoft Outlook, let Odoo in charge of sending emails
        Otherwise, Microsoft Outlook will send them
        """
        with microsoft_calendar_token(self.env.user.sudo()) as token:
            if not token:
                super()._send_mail_to_attendees(mail_template, force_send)
