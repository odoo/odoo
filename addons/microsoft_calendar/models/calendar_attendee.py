# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token


class Attendee(models.Model):
    _name = 'calendar.attendee'
    _inherit = 'calendar.attendee'

    def _send_mail_to_attendees(self, template_xmlid, force_send=False, ignore_recurrence=False):
        """ Override the super method
        If not synced with Microsoft Outlook, let Odoo in charge of sending emails
        Otherwise, Microsoft Outlook will send them
        """
        with microsoft_calendar_token(self.env.user.sudo()) as token:
            if not token:
                super()._send_mail_to_attendees(template_xmlid, force_send, ignore_recurrence)
