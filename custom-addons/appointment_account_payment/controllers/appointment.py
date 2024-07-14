# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from babel.dates import format_datetime
from werkzeug.exceptions import NotFound

from odoo import Command, fields, http
from odoo.http import request
from odoo.addons.appointment.controllers.appointment import AppointmentController
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.payment import utils as payment_utils
from odoo.tools.misc import get_lang


class AppointmentAccountPayment(AppointmentController):

    @http.route(['/calendar_booking/<string:booking_token>/cancel'], type='http', auth="public", website=True, sitemap=False)
    def calendar_booking_cancel(self, booking_token):
        """ Cancel the booking linked to booking_token if any, unlink it, and redirect
            to the page of corresponding appointment to take another appointment """
        booking_sudo = request.env['calendar.booking'].sudo().search([('booking_token', '=', booking_token)], limit=1)
        if not booking_sudo or booking_sudo.calendar_event_id:
            raise NotFound()

        appointment_type = booking_sudo.appointment_type_id
        invitation_params = booking_sudo.appointment_invite_id._get_invitation_url_parameters()
        booking_sudo.unlink()
        return request.redirect(f"/appointment/{appointment_type.id}?{keep_query(*invitation_params)}")

    @http.route(['/calendar_booking/<string:booking_token>/view'], type='http', auth="public", website=True, sitemap=False)
    def calendar_booking_view(self, booking_token):
        """ View the booking summary. This is accessed at the end of the appointment flow when
            the payment is pending or failed / was cancelled. Once paid, a calendar_event is created. If
            it exists, redirect to that calendar event page instead. """
        booking_sudo = request.env['calendar.booking'].sudo().search([('booking_token', '=', booking_token)], limit=1)
        if not booking_sudo:
            raise NotFound()
        if booking_sudo.calendar_event_id:
            return request.redirect(
                "/calendar/view/{event_token}?partner_id={pid}&{args}".format(
                    event_token=booking_sudo.calendar_event_id.access_token,
                    pid=booking_sudo.partner_id.id,
                    args=keep_query(*booking_sudo.appointment_invite_id._get_invitation_url_parameters(), state='new')
                ))

        timezone = (request.session.get('timezone') or
                    request.env.context.get('tz') or
                    booking_sudo.appointment_type_id.appointment_tz)
        start_tz = fields.Datetime.from_string(booking_sudo.start).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezone))
        locale = get_lang(request.env).code
        start_dt = f"{format_datetime(start_tz, 'EEE', locale=locale)} {format_datetime(start_tz, locale=locale)}"

        return request.render("appointment_account_payment.calendar_booking_view", {
            'attendees': (booking_sudo.partner_id | booking_sudo.staff_user_id.partner_id) if booking_sudo.staff_user_id else booking_sudo.partner_id,
            'booking': booking_sudo,
            'start_dt': start_dt,
            'timezone': timezone,
        })

    def _handle_appointment_form_submission(
        self, appointment_type,
        date_start, date_end, duration,
        description, answer_input_values, name, customer, appointment_invite, guests=None,
        staff_user=None, asked_capacity=1, booking_line_values=None
    ):
        """ Override: when a payment step is necessary, we create the calendar booking model to store all relevant information
            instead of creating an calendar.event. This prevents synchronizing calendars with non-confirmed events. It will
            be transformed to a calendar.event on payment (or confirmation). See _make_event_from_paid_booking on calendar.booking.
            Redirects to payment if needed. See _redirect_to_payment"""
        if appointment_type.has_payment_step and appointment_type.product_id.lst_price:
            calendar_booking = request.env['calendar.booking'].sudo().create([{
                'appointment_answer_input_ids': [Command.create(vals) for vals in answer_input_values],
                'appointment_invite_id': appointment_invite.id,
                'appointment_type_id': appointment_type.id,
                'booking_line_ids': [Command.create(vals) for vals in booking_line_values],
                'asked_capacity': asked_capacity,
                'description': description,
                'guest_ids': [Command.link(pid) for pid in guests.ids] if guests else [],
                'name': name,
                'partner_id': customer.id,
                'product_id': appointment_type.product_id.id,
                'staff_user_id': staff_user.id,
                'start': date_start,
                'stop': date_end,
            }])
            return self._redirect_to_payment(calendar_booking)

        return super()._handle_appointment_form_submission(
            appointment_type, date_start, date_end, duration, description, answer_input_values, name,
            customer, appointment_invite, guests, staff_user, asked_capacity, booking_line_values
        )

    def _redirect_to_payment(self, calendar_booking):
        """ Redirection method called from appointment form submission when the flow has a payment step.
            This method does two things. First, it creates a draft invoice linked to the current booking.
            A new invoice is created each time a booking is created after filling the form. Second, it
            redirects to the /payment route of appointment, the payment page, allowing specific pre processing.
            This method is overriden if eCommerce is installed to use use sale orders instead. """
        invoice = calendar_booking.sudo()._make_invoice_from_booking()
        if not invoice:
            raise NotFound()

        return request.redirect(
            "/payment/pay?appointment_type_id={aid}&invoice_id={iid}&partner_id={pid}&amount={amount}&access_token={token}&{args}".format(
                aid=calendar_booking.appointment_type_id.id,
                iid=invoice.id,
                pid=calendar_booking.partner_id.id,
                amount=invoice.amount_total,
                token=payment_utils.generate_access_token(invoice.partner_id.id, invoice.amount_total, invoice.currency_id.id),
                args=keep_query('*')
            ))
