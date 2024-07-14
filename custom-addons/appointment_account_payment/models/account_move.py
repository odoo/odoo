# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    calendar_booking_ids = fields.One2many("calendar.booking", "account_move_id", string="Meeting Booking")

    def _invoice_paid_hook(self):
        """ Override: when an invoice linked to appointment bookings is paid,
            create events corresponding to the calendar bookings """
        res = super()._invoice_paid_hook()
        self.calendar_booking_ids._make_event_from_paid_booking()
        return res
