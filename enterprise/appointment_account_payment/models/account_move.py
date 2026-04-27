# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    calendar_booking_ids = fields.One2many("calendar.booking", "account_move_id", string="Meeting Booking")

    def _post(self, soft=True):
        """ Either when posting manually or when transaction is done. """
        posted = super()._post(soft=soft)
        posted.calendar_booking_ids._make_event_from_paid_booking()
        return posted
