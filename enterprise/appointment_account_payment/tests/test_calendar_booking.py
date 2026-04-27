# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.appointment_account_payment.tests.common import AppointmentAccountPaymentCommon
from odoo.tests import users, tagged
from odoo.tools import mute_logger

from unittest.mock import patch
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time


@tagged("post_install", "-at_install")
class AppointmentAccountPaymentTest(AppointmentAccountPaymentCommon):

    @mute_logger('odoo.sql_db')
    @users('apt_manager')
    def test_booking_to_event_on_invoice_paid_resource(self):
        """ Replace booking with Event when invoice is paid - resource appointment """
        appointment_type = self.appointment_resources_payment
        asked_capacity = 5
        start = self.start_slot
        stop = self.stop_slot

        # Assert Initial Capacity
        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 5)

        # Create Calendar Event Booking and Calendar Booking Lines
        booking_values = {
            'appointment_type_id': appointment_type.id,
            'asked_capacity': asked_capacity,
            'duration': 1.0,
            'partner_id': self.apt_manager.partner_id.id,
            'product_id': appointment_type.product_id.id,
            'start': start,
            'stop': stop,
        }
        calendar_booking = self.env['calendar.booking'].create(booking_values)
        calendar_booking_lines_values = {}
        for resource in appointment_type.resource_ids:
            resource_remaining_capacity = resources_remaining_capacity.get(resource)
            new_capacity_reserved = min(resource_remaining_capacity, asked_capacity, resource.capacity)
            asked_capacity -= new_capacity_reserved
            calendar_booking_lines_values[resource.id] = {
                'appointment_resource_id': resource.id,
                'calendar_booking_id': calendar_booking.id,
                'capacity_reserved': new_capacity_reserved,
                'capacity_used': new_capacity_reserved if resource.shareable and appointment_type.resource_manage_capacity else resource.capacity,
            }
        self.env['calendar.booking.line'].create(calendar_booking_lines_values.values())

        # Assert Booking Lines are not taking capacity
        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 5)

        # Create an invoice
        invoice = calendar_booking.sudo()._make_invoice_from_booking()
        self.assertEqual(calendar_booking.account_move_id, invoice)
        self.assertFalse(invoice.calendar_booking_ids.calendar_event_id)

        # Posting invoice (at transaction post processing or manually) creates event and reserve space
        invoice._post()
        event = invoice.calendar_booking_ids.calendar_event_id
        self.assertEqual(len(event), 1)
        self.assertTrue(invoice.calendar_booking_ids.calendar_event_id)
        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 0)

        # Inoviced quantity should be equal to asked_capacity
        self.assertEqual(invoice.invoice_line_ids.quantity, calendar_booking.asked_capacity)

        # Assert Booking Data
        self.assertTrue(event.active)
        self.assertEqual(event, calendar_booking.calendar_event_id)
        self.assertEqual(event.appointment_type_id, calendar_booking.appointment_type_id)
        self.assertEqual(event.resource_total_capacity_reserved, calendar_booking.asked_capacity)
        self.assertEqual(event.resource_total_capacity_used, calendar_booking.asked_capacity)
        self.assertEqual(event.duration, calendar_booking.duration)
        self.assertEqual(event.partner_ids, calendar_booking.partner_id)
        self.assertEqual(event.start, calendar_booking.start)
        self.assertEqual(event.stop, calendar_booking.stop)
        self.assertTrue(all(attendee.state == 'accepted' for attendee in event.attendee_ids))

        # Assert Booking Lines Data
        booking_line_1 = event.booking_line_ids.filtered(lambda line: line.appointment_resource_id == self.resource_1)
        booking_line_2 = event.booking_line_ids.filtered(lambda line: line.appointment_resource_id == self.resource_2)
        self.assertEqual(len(booking_line_1 + booking_line_2), 2)
        for booking_line in (booking_line_1 | booking_line_2):
            calendar_booking_line = calendar_booking.booking_line_ids.filtered(
                lambda line: line.appointment_resource_id == booking_line.appointment_resource_id)
            self.assertTrue(calendar_booking_line)
            self.assertTrue(booking_line.active)
            self.assertEqual(booking_line.capacity_reserved, calendar_booking_line.capacity_reserved)
            self.assertEqual(booking_line.capacity_used, calendar_booking_line.capacity_used)
            self.assertEqual(booking_line.event_start, calendar_booking.start)
            self.assertEqual(booking_line.event_stop, calendar_booking.stop)

    @mute_logger('odoo.sql_db')
    @freeze_time('2022-2-13 20:00:00')
    @users('apt_manager')
    def test_booking_to_event_on_invoice_paid_users(self):
        """ Replace booking with Event when invoice is paid - staff user appointment """
        appointment_type = self.appointment_users_payment
        start = self.start_slot
        stop = self.stop_slot

        # Assert Initial Data
        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 1)

        # Create Calendar Event Booking
        booking_values = {
            'appointment_type_id': appointment_type.id,
            'duration': 1.0,
            'partner_id': self.apt_manager.partner_id.id,
            'product_id': appointment_type.product_id.id,
            'staff_user_id': self.staff_user_bxls.id,
            'start': start,
            'stop': stop,
        }
        calendar_booking = self.env['calendar.booking'].create(booking_values)

        # Create an invoice
        invoice = calendar_booking.sudo()._make_invoice_from_booking()
        self.assertEqual(calendar_booking.account_move_id, invoice)
        self.assertFalse(invoice.calendar_booking_ids.calendar_event_id)

        # Calendar Booking do not reserve space
        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 1)

        # Posting invoice (at transaction post processing or manually) creates event and reserve space
        invoice._post()
        event = invoice.calendar_booking_ids.calendar_event_id
        self.assertEqual(len(event), 1)
        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 0)

        # Assert Booking Data
        self.assertTrue(event.active)
        self.assertEqual(event, calendar_booking.calendar_event_id)
        self.assertEqual(event.appointment_type_id, calendar_booking.appointment_type_id)
        self.assertEqual(event.duration, calendar_booking.duration)
        self.assertEqual(event.user_id, calendar_booking.staff_user_id)
        self.assertEqual(event.partner_ids, calendar_booking.partner_id | calendar_booking.staff_user_id.partner_id)
        self.assertEqual(event.start, calendar_booking.start)
        self.assertEqual(event.stop, calendar_booking.stop)
        self.assertTrue(all(attendee.state == 'accepted' for attendee in event.attendee_ids))

    def test_booking_unlink(self):
        """ Unlinking a booking should (only) unlink appointment answers not linked to any calendar event. """
        appointment_type = self.appointment_users_payment
        appointment_question = self.env['appointment.question'].create({
            'appointment_type_id': appointment_type.id,
            'name': 'How are you ?',
            'question_type': 'char',
        })
        appointment_answer_input_values = {
            'appointment_type_id': appointment_type.id,
            'question_id': appointment_question.id,
            'value_text_box': 'I am Good',
        }
        # Create Calendar Event Booking
        booking_values = {
            'appointment_type_id': appointment_type.id,
            'appointment_answer_input_ids': [Command.create(appointment_answer_input_values)],
            'duration': 1.0,
            'partner_id': self.apt_manager.partner_id.id,
            'product_id': appointment_type.product_id.id,
            'staff_user_id': self.staff_user_bxls.id,
            'start': self.start_slot,
            'stop': self.stop_slot,
        }
        calendar_booking = self.env['calendar.booking'].create(booking_values)
        self.assertFalse(calendar_booking.calendar_event_id)
        answer_inputs = calendar_booking.appointment_answer_input_ids
        self.assertEqual(len(answer_inputs), 1)

        calendar_booking.unlink()
        self.assertFalse(answer_inputs.exists())

        calendar_booking = self.env['calendar.booking'].create(booking_values)
        answer_inputs = calendar_booking.appointment_answer_input_ids
        calendar_booking._make_event_from_paid_booking()
        self.assertTrue(answer_inputs.calendar_event_id)

        calendar_booking.unlink()
        self.assertTrue(answer_inputs.exists())

    @users('apt_manager')
    def test_contiguous_bookings_availability(self):
        """ Checks that two bookings with the same user (or resource) are both considered as available on contiguous slots. """
        booking_values = {
            'appointment_type_id': self.appointment_users_payment.id,
            'duration': 1.0,
            'partner_id': self.apt_manager.partner_id.id,
            'product_id': self.appointment_users_payment.product_id.id,
            'staff_user_id': self.staff_user_bxls.id,
        }
        calendar_bookings = self.env['calendar.booking'].create([{
            'start': self.start_slot,
            'stop': self.stop_slot,
            **booking_values
        }, {
            'start': self.stop_slot,
            'stop': self.stop_slot + relativedelta(hours=1),
            **booking_values
        }])
        self.assertFalse(calendar_bookings._filter_unavailable_bookings())
        calendar_bookings._make_event_from_paid_booking()
        self.assertEqual(len(calendar_bookings.calendar_event_id), 2)

    def test_gc_calendar_booking(self):
        """ Remove bookings still existing after 6 months.
            Remove bookings with ending passed for 2 months at least. """
        max_creation_dt = self.reference_now - relativedelta(months=6)
        max_stop_dt = self.reference_now - relativedelta(months=2)

        with patch.object(self.env.cr, 'now', lambda: max_creation_dt - relativedelta(months=1)):
            booking_1, booking_2 = self.env['calendar.booking'].create([{
                'start': max_stop_dt + relativedelta(hours=1),
                'stop': max_stop_dt + relativedelta(hours=2),
                'appointment_type_id': self.appointment_users_payment.id,
                'product_id': self.appointment_users_payment.product_id.id,
            }, {
                'start': max_stop_dt - relativedelta(hours=2),
                'stop': max_stop_dt - relativedelta(hours=1),
                'appointment_type_id': self.appointment_users_payment.id,
                'product_id': self.appointment_users_payment.product_id.id,
            }])
        with patch.object(self.env.cr, 'now', lambda: self.reference_now):
            booking_3, booking_4 = self.env['calendar.booking'].create([{
                'start': max_stop_dt + relativedelta(hours=1),
                'stop': max_stop_dt + relativedelta(hours=2),
                'appointment_type_id': self.appointment_users_payment.id,
                'product_id': self.appointment_users_payment.product_id.id,
            }, {
                'start': max_stop_dt - relativedelta(hours=2),
                'stop': max_stop_dt - relativedelta(hours=1),
                'appointment_type_id': self.appointment_users_payment.id,
                'product_id': self.appointment_users_payment.product_id.id,
            }])

        with freeze_time(self.reference_now):
            self.env['calendar.booking']._gc_calendar_booking()

        self.assertFalse(booking_1.exists())
        self.assertFalse(booking_2.exists())
        self.assertTrue(booking_3.exists())
        self.assertFalse(booking_4.exists())
