# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from collections import defaultdict
from datetime import datetime
from markupsafe import escape, Markup

from odoo import api, Command, fields, models, _
from odoo.tools import format_date, format_time


class CalendarBooking(models.Model):
    """ This model is only used to store appointment informations for bookings WITH PAYMENT
        When we consider it is paid, the calendar event is created and GC will remove the booking. """
    _name = "calendar.booking"
    _description = "Meeting Booking"
    _order = "start desc, id desc"

    def _default_booking_token(self):
        return uuid.uuid4().hex

    # Answers
    appointment_answer_input_ids = fields.One2many('appointment.answer.input', 'calendar_booking_id', string="Appointment Answers")
    # Calendar Event Data
    appointment_invite_id = fields.Many2one('appointment.invite')
    appointment_type_id = fields.Many2one('appointment.type', ondelete="cascade", required=True)
    duration = fields.Float('Duration', compute="_compute_duration")
    guest_ids = fields.Many2many('res.partner', string="Guests")
    name = fields.Char('Customer Name')  # Could differ from partner
    partner_id = fields.Many2one('res.partner', 'Contact')
    start = fields.Datetime('Start', required=True)
    stop = fields.Datetime('Stop', required=True)
    # Resources
    asked_capacity = fields.Integer('Asked Capacity', default=0)
    booking_line_ids = fields.One2many('calendar.booking.line', 'calendar_booking_id', string="Booking Lines")
    # Staff User
    staff_user_id = fields.Many2one('res.users', 'Operator')
    # Payment
    account_move_id = fields.Many2one("account.move", string="Appointment Invoice", readonly=True)
    product_id = fields.Many2one('product.product', required=True)
    # Access for front-end view
    booking_token = fields.Char('Access Token', default=_default_booking_token, readonly=True)
    # Used in display
    not_available = fields.Boolean('Is Not Available')
    # Event (once created)
    calendar_event_id = fields.Many2one('calendar.event', 'Meeting')

    @api.depends('start', 'stop')
    def _compute_duration(self):
        for booking in self:
            booking.duration = (booking.stop - booking.start).total_seconds() / 3600

    def unlink(self):
        # Unlink answers linked to these bookings that do not belong to meetings.
        answers = self.appointment_answer_input_ids.filtered(lambda answer: not answer.calendar_event_id)
        answers.unlink()
        return super().unlink()

    def _filter_unavailable_bookings(self):
        """ Check availability in recordset self and returns bookings that would not be
            available when trying to reserving space for all of them. This method will try
            to 'fit' as much as possible availability, in a simple approach. """
        user_bookings = self.filtered("staff_user_id")
        resource_bookings = self.filtered("booking_line_ids")
        if not user_bookings and not resource_bookings:
            return self

        available_user_bookings = self.env['calendar.booking']
        for staff_user, staff_user_bookings in user_bookings.grouped("staff_user_id").items():
            last_booking_end = datetime.min
            for booking in staff_user_bookings.sorted('stop'):  # sorting by end allows maximum coverage
                if (booking.start >= last_booking_end and
                    staff_user.partner_id.calendar_verify_availability(booking.start, booking.stop)):
                    available_user_bookings += booking
                    last_booking_end = booking.stop

        available_resource_bookings = resource_bookings
        boundaries = sorted(set(resource_bookings.mapped('start') + resource_bookings.mapped('stop')))
        for index, start in enumerate(boundaries[:-1]):
            stop = boundaries[index + 1]
            interval_bookings = available_resource_bookings.filtered(lambda booking: booking.start < stop and booking.stop > start)
            for resource, booking_lines in interval_bookings.booking_line_ids.grouped("appointment_resource_id").items():
                booking_lines &= available_resource_bookings.booking_line_ids
                total_resource_availability = resource.appointment_type_ids[0]._get_resources_remaining_capacity(
                    resource, start, stop, with_linked_resources=False
                )['total_remaining_capacity'] if booking_lines and resource.appointment_type_ids else 0
                for booking_line in booking_lines:
                    if total_resource_availability >= booking_line.capacity_used:
                        total_resource_availability -= booking_line.capacity_used
                    else:
                        available_resource_bookings -= booking_lines.calendar_booking_id

        return self - (available_user_bookings | available_resource_bookings)

    def _get_description(self):
        """ Returns a multiline description of the booking """
        self.ensure_one()
        tz = self.env.context.get('tz') or self.partner_id.tz or self.appointment_type_id.appointment_tz
        env_tz = self.with_context(tz=tz).env
        if self.staff_user_id:
            return _(
                "%(name)s with %(staff_user)s\n%(date_start)s at %(time_start)s to\n%(date_end)s at %(time_end)s (%(timezone)s)",
                name=self.appointment_type_id.name,
                staff_user=self.staff_user_id.display_name,
                date_start=format_date(env_tz, self.start),
                time_start=format_time(env_tz, self.start, tz=tz),
                date_end=format_date(env_tz, self.stop),
                time_end=format_time(env_tz, self.stop, tz=tz),
                timezone=tz,
            )
        else:
            return _(
                "%(name)s\n%(date_start)s at %(time_start)s to\n%(date_end)s at %(time_end)s (%(timezone)s)",
                name=self.appointment_type_id.name,
                staff_user=self.staff_user_id.display_name,
                date_start=format_date(env_tz, self.start),
                time_start=format_time(env_tz, self.start, tz=tz),
                date_end=format_date(env_tz, self.stop),
                time_end=format_time(env_tz, self.stop, tz=tz),
                timezone=tz,
            )

    def _log_booking_collisions(self):
        """ Logs an error message on reference invoice listing the bookings that were not
            successfully made into meetings when confirming / paying the invoice.
        """
        odoobot = self.env.ref('base.partner_root')
        for booking in self.filtered("account_move_id"):
            booking.account_move_id._message_log(
                body=Markup("<p>%s</p>") % escape(
                    _("The following booking was not confirmed due to insufficient availability or configuration changes: %s")
                ) % booking._get_html_link(),
                author_id=odoobot.id
            )

    def _make_event_from_paid_booking(self):
        """ This method is called when the booking is considered as paid. We create a calendar event from the booking values. """
        if not self:
            return
        todo = self.filtered(lambda booking: not booking.calendar_event_id)
        unavailable_bookings = todo._filter_unavailable_bookings()

        for booking in todo - unavailable_bookings:
            booking_line_values = [{
                'appointment_resource_id': line.appointment_resource_id.id,
                'capacity_reserved': line.capacity_reserved,
                'capacity_used': line.capacity_used,
            } for line in booking.booking_line_ids]

            calendar_event_values = booking.appointment_type_id._prepare_calendar_event_values(
                booking.asked_capacity, booking_line_values, booking.duration, booking.appointment_invite_id,
                booking.guest_ids, booking.name, booking.partner_id, booking.staff_user_id, booking.start, booking.stop
            )
            calendar_event_values['appointment_answer_input_ids'] = [Command.set(booking.appointment_answer_input_ids.ids)]

            meeting = self.env['calendar.event'].with_context(
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notify_author=True,
                allowed_company_ids=booking.staff_user_id.company_ids.ids,
            ).sudo().create(calendar_event_values)
            booking.calendar_event_id = meeting

        unavailable_bookings.not_available = True
        unavailable_bookings._log_booking_collisions()

    def _make_invoice_from_booking(self):
        """ Create, link and return invoices for current bookings.
            Call in sudo mode to avoid access error on invoice creation. """
        return self.env['account.move'].create([{
            'calendar_booking_ids': [Command.link(booking.id)],
            'invoice_line_ids': [Command.create({
                'display_type': 'product',
                'name': booking._get_description(),
                'product_id': booking.product_id.id,
                'quantity': booking.asked_capacity or 1.0,
            })],
            'move_type': 'out_invoice',
            'partner_id': booking.partner_id.id,
        } for booking in self])

    @api.autovacuum
    def _gc_calendar_booking(self):
        max_creation_dt = fields.Datetime.subtract(fields.Datetime.now(), months=6)
        max_ending_dt = fields.Datetime.subtract(fields.Datetime.now(), months=2)
        domain = [
            '|',
            ('create_date', '<', max_creation_dt),
            ('stop', '<', max_ending_dt)
        ]
        return self.sudo().search(domain).unlink()
