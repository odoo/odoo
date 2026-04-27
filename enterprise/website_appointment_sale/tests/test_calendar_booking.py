# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.appointment_account_payment.tests.common import AppointmentAccountPaymentCommon
from odoo.tests import users
from odoo.tools import mute_logger


class WebsiteAppointmentSaleTest(AppointmentAccountPaymentCommon):

    @mute_logger('odoo.sql_db')
    @users('apt_manager')
    def test_booking_to_event_collisions_resources(self):
        """ Checks that a booking does not add a sale order line in cart if it would then
            overflow the resource capacity. Check that event is not created when resources
            are not available anymore. """
        appointment_type = self.appointment_resources_payment
        # Resource remaining: capacity 2 (shareable)
        self.resource_1.unlink()
        asked_capacity = 2
        start = self.start_slot
        stop = self.stop_slot

        # Assert Initial Capacity
        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 2)

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
        calendar_booking_line_values = {
            'appointment_resource_id': self.resource_2.id,
            'capacity_reserved': asked_capacity,
            'capacity_used': asked_capacity,
        }

        calendar_booking_1 = self.env['calendar.booking'].create(booking_values)
        calendar_booking_line_values['calendar_booking_id'] = calendar_booking_1.id
        self.env['calendar.booking.line'].create(calendar_booking_line_values)
        sale_order_1 = self.env['sale.order'].sudo().create({'partner_id': calendar_booking_1.partner_id.id})
        cart_values = sale_order_1._cart_update(
            product_id=appointment_type.product_id.id,
            set_qty=1,
            calendar_booking_id=calendar_booking_1.id,
        )
        self.assertEqual(cart_values['quantity'], 1)
        sale_order_line_1 = sale_order_1.order_line.filtered(lambda line: line.id == cart_values['line_id'])
        self.assertTrue(sale_order_line_1)
        self.assertFalse(sale_order_line_1.calendar_event_id)

        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 2)

        calendar_booking_2 = self.env['calendar.booking'].create(booking_values)
        calendar_booking_line_values['calendar_booking_id'] = calendar_booking_2.id
        self.env['calendar.booking.line'].create(calendar_booking_line_values)
        sale_order_2 = self.env['sale.order'].sudo().create({'partner_id': calendar_booking_2.partner_id.id})

        # In sale_order_1, resource is already booked for max capacity. Line is not added.
        self.assertTrue((sale_order_1.order_line.calendar_booking_ids | calendar_booking_2)._filter_unavailable_bookings())
        self.assertFalse((sale_order_2.order_line.calendar_booking_ids | calendar_booking_2)._filter_unavailable_bookings())
        cart_values = sale_order_2._cart_update(
            product_id=appointment_type.product_id.id,
            set_qty=1,
            calendar_booking_id=calendar_booking_2.id,
        )
        self.assertEqual(cart_values['quantity'], 1)
        sale_order_line_2 = sale_order_2.order_line.filtered(lambda line: line.id == cart_values['line_id'])
        self.assertTrue(sale_order_line_2)
        self.assertFalse(sale_order_line_2.calendar_event_id)

        sale_order_1._action_confirm()
        sale_order_2._action_confirm()
        # sale_order_2 failed since resource is not available anymore
        self.assertTrue(calendar_booking_1.calendar_event_id)
        self.assertTrue(sale_order_1.calendar_event_count == 1)
        self.assertTrue(calendar_booking_2.not_available and not calendar_booking_2.calendar_event_id)
        self.assertTrue(sale_order_2.calendar_event_count == 0)

        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 0)

    @freeze_time('2022-2-13 20:00:00')
    @mute_logger('odoo.sql_db')
    @users('apt_manager')
    def test_booking_to_event_collisions_users(self):
        """ Checks that a booking does not add a sale order line in cart when it already contains a
            booking with the selected staff_user on the same slot. Check that event is not created
            when users are not available anymore. """
        appointment_type = self.appointment_users_payment
        start = self.start_slot
        stop = self.stop_slot

        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 1)

        booking_values = {
            'appointment_type_id': appointment_type.id,
            'duration': 1.0,
            'partner_id': self.apt_manager.partner_id.id,
            'product_id': appointment_type.product_id.id,
            'staff_user_id': self.staff_user_bxls.id,
            'start': start,
            'stop': stop,
        }
        calendar_booking_1 = self.env['calendar.booking'].create(booking_values)
        sale_order_1 = self.env['sale.order'].sudo().create({'partner_id': calendar_booking_1.partner_id.id})
        cart_values = sale_order_1._cart_update(
            product_id=appointment_type.product_id.id,
            set_qty=1,
            calendar_booking_id=calendar_booking_1.id,
        )
        self.assertEqual(cart_values['quantity'], 1)
        sale_order_line_1 = sale_order_1.order_line.filtered(lambda line: line.id == cart_values['line_id'])
        self.assertTrue(sale_order_line_1)
        self.assertFalse(sale_order_line_1.calendar_event_id)

        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 1)

        calendar_booking_2 = self.env['calendar.booking'].create(booking_values)
        sale_order_2 = self.env['sale.order'].sudo().create({'partner_id': calendar_booking_2.partner_id.id})

        # In sale_order_1, apt_manager is already booked for that slot. Line would not be added.
        self.assertTrue((sale_order_1.order_line.calendar_booking_ids | calendar_booking_2)._filter_unavailable_bookings())
        self.assertFalse((sale_order_2.order_line.calendar_booking_ids | calendar_booking_2)._filter_unavailable_bookings())
        cart_values = sale_order_2._cart_update(
            product_id=appointment_type.product_id.id,
            set_qty=1,
            calendar_booking_id=calendar_booking_2.id,
        )
        self.assertEqual(cart_values['quantity'], 1)
        sale_order_line_2 = sale_order_2.order_line.filtered(lambda line: line.id == cart_values['line_id'])
        self.assertTrue(sale_order_line_2)
        self.assertFalse(sale_order_line_2.calendar_event_id)

        sale_order_1._action_confirm()
        sale_order_2._action_confirm()
        # sale_order_2 failed since slot is not available anymore
        self.assertTrue(calendar_booking_1.calendar_event_id)
        self.assertTrue(sale_order_1.calendar_event_count == 1)
        self.assertTrue(calendar_booking_2.not_available and not calendar_booking_2.calendar_event_id)
        self.assertTrue(sale_order_2.calendar_event_count == 0)

        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 0)

    @mute_logger('odoo.sql_db')
    @users('apt_manager')
    def test_booking_to_event_on_so_confirmation_resource(self):
        """ Replace booking with Event when SO is confirmed - resource appointment """
        appointment_type = self.appointment_resources_payment
        asked_capacity = 3
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
        calendar_booking_line_values = {
            'appointment_resource_id': self.resource_1.id,
            'calendar_booking_id': calendar_booking.id,
            'capacity_reserved': asked_capacity,
            'capacity_used': asked_capacity
        }
        calendar_booking_line = self.env['calendar.booking.line'].create(calendar_booking_line_values)

        # Assert Booking Lines are not taking capacity
        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 5)

        # Create SO and SOL linked to booking
        sale_order = self.env['sale.order'].sudo().create({'partner_id': calendar_booking.partner_id.id})
        self.assertFalse(calendar_booking._filter_unavailable_bookings())
        cart_values = sale_order._cart_update(
            product_id=appointment_type.product_id.id,
            set_qty=1,
            calendar_booking_id=calendar_booking.id,
        )
        self.assertEqual(cart_values['quantity'], 1)
        sale_order_line = sale_order.order_line.filtered(lambda line: line.id == cart_values['line_id'])
        self.assertTrue(sale_order_line)
        self.assertEqual(sale_order_line.calendar_booking_ids, calendar_booking)
        self.assertFalse(sale_order_line.calendar_event_id)

        # Confirm the SO
        sale_order._action_confirm()
        event = sale_order_line.calendar_event_id
        self.assertTrue(event)
        self.assertEqual(event, calendar_booking.calendar_event_id)

        # Assert Capacity is Reduced to 2
        resources_remaining_capacity = appointment_type._get_resources_remaining_capacity(appointment_type.resource_ids, start, stop)
        self.assertEqual(resources_remaining_capacity['total_remaining_capacity'], 2)

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
        booking_line = event.booking_line_ids
        self.assertEqual(len(booking_line), 1)
        self.assertTrue(booking_line.active)
        self.assertEqual(booking_line.appointment_resource_id, calendar_booking_line.appointment_resource_id)
        self.assertEqual(booking_line.appointment_type_id, appointment_type)
        self.assertEqual(booking_line.capacity_reserved, calendar_booking_line.capacity_reserved)
        self.assertEqual(booking_line.capacity_used, calendar_booking_line.capacity_used)
        self.assertEqual(booking_line.event_start, calendar_booking.start)
        self.assertEqual(booking_line.event_stop, calendar_booking.stop)

    @freeze_time('2022-2-13 20:00:00')
    @mute_logger('odoo.sql_db')
    @users('apt_manager')
    def test_booking_to_event_on_so_confirmation_users(self):
        """ Replace booking with Event when invoice is paid - staff user appointment """
        appointment_type = self.appointment_users_payment
        start = self.start_slot
        stop = self.stop_slot

        # Assert Initial Data
        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 1)

        # Create Calendar Event Booking and Calendar Booking Lines
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

        # Create SO and SOL linked to booking
        sale_order = self.env['sale.order'].sudo().create({'partner_id': calendar_booking.partner_id.id})
        self.assertFalse(calendar_booking._filter_unavailable_bookings())
        cart_values = sale_order._cart_update(
            product_id=appointment_type.product_id.id,
            set_qty=1,
            calendar_booking_id=calendar_booking.id,
        )
        self.assertEqual(cart_values['quantity'], 1)
        sale_order_line = sale_order.order_line.filtered(lambda line: line.id == cart_values['line_id'])
        self.assertTrue(sale_order_line)
        self.assertEqual(sale_order_line.calendar_booking_ids, calendar_booking)
        self.assertFalse(sale_order_line.calendar_event_id)

        # Calendar Booking do not reserve space
        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 1)

        sale_order._action_confirm()
        event = sale_order_line.calendar_event_id
        self.assertTrue(event)
        self.assertEqual(event, calendar_booking.calendar_event_id)

        # Space is now reserved
        slots = appointment_type._get_appointment_slots('UTC')
        slots_list = self._filter_appointment_slots(slots)
        self.assertEqual(len(slots_list), 0, "Confirming the SO with SOL linked to a booking creates an event booking the slot")

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
