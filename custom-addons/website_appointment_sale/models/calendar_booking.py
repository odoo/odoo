# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import escape, Markup

from odoo import _, fields, models


class CalendarBooking(models.Model):
    _inherit = "calendar.booking"

    order_line_id = fields.Many2one("sale.order.line", 'Sale Order Line', ondelete="cascade")

    def _make_event_from_paid_booking(self):
        """ Override: link calendar event to SOL when created """
        super()._make_event_from_paid_booking()
        for booking in self.filtered("order_line_id"):
            booking.order_line_id.calendar_event_id = booking.calendar_event_id

    def _log_booking_collisions(self):
        super()._log_booking_collisions()
        odoobot = self.env.ref('base.partner_root')
        for order, order_lines in self.order_line_id.grouped("order_id").items():
            order._message_log(
                body=Markup("<p>%s</p>") % escape(
                    _("The following bookings were not confirmed due to insufficient availability or configuration changes: %s")
                ) % Markup(', ').join([
                    booking._get_html_link() for booking in order_lines.calendar_booking_ids
                ]),
                author_id=odoobot.id
            )
