# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo import Command, exceptions
from odoo.addons.test_event_full.tests.common import TestEventFullCommon
from odoo.tests.common import users


class TestEventEvent(TestEventFullCommon):

    @users('event_user')
    def test_event_create_wtype(self):
        """ Test a single event creation with a type defining all sub records. """
        event_type = self.env['event.type'].browse(self.test_event_type.ids)

        event_values = dict(
            self.event_base_vals,
            event_type_id=event_type.id,
        )
        event = self.env['event.event'].create([event_values])
        event.write({
            'event_ticket_ids': [
                Command.update(
                    event.event_ticket_ids[0].id,
                    {'start_sale_datetime': self.reference_now + timedelta(hours=1)},
                ),
                Command.update(
                    event.event_ticket_ids[1].id,
                    {'start_sale_datetime': self.reference_now + timedelta(hours=2)},
                )
            ],
        })

        # check result
        self.assertEqual(event.address_id, self.env.user.company_id.partner_id)
        self.assertEqual(event.country_id, self.env.user.company_id.country_id)
        self.assertEqual(event.date_tz, 'Europe/Paris')
        self.assertEqual(event.event_booth_count, 4)
        self.assertEqual(len(event.event_mail_ids), 3)
        self.assertEqual(len(event.event_ticket_ids), 2)
        self.assertTrue(event.introduction_menu)
        self.assertEqual(event.message_partner_ids, self.env.user.partner_id)
        self.assertEqual(event.note, '<p>Template note</p>')
        self.assertTrue(event.register_menu)
        self.assertEqual(len(event.question_ids), 3)
        self.assertTrue(event.seats_limited)
        self.assertEqual(event.seats_max, 30)
        self.assertEqual(event.stage_id, self.stage_def)
        self.assertEqual(event.tag_ids, self.tags)
        self.assertTrue(event.website_menu)

        # check time dependent computation: before event
        with freeze_time(self.reference_now):
            self.assertFalse(event.is_finished)
            self.assertFalse(event.is_ongoing)
            self.assertFalse(event.event_registrations_started)

        # check time dependent computation: registrations started
        with freeze_time(self.reference_now + timedelta(hours=1)):
            event.invalidate_model(['is_finished', 'is_ongoing', 'event_registrations_started'])
            self.assertFalse(event.is_finished)
            self.assertFalse(event.is_ongoing)
            self.assertTrue(event.event_registrations_started)

        # check time dependent computation: during event
        with freeze_time(self.reference_now + timedelta(days=1, hours=1)):
            event.invalidate_model(['is_finished', 'is_ongoing', 'event_registrations_started'])
            self.assertFalse(event.is_finished)
            self.assertTrue(event.is_ongoing)
            self.assertTrue(event.event_registrations_started)

    def test_event_kanban_state_on_stage_change(self):
        """Test that kanban_state updates correctly when stage is changed."""
        test_event_1 = self.env['event.event'].browse(self.test_event.ids)
        test_event_2 = test_event_1.copy()

        test_event_1.kanban_state = 'done'
        test_event_2.kanban_state = 'cancel'  # Event Cancelled

        new_stage = self.env['event.stage'].create({'name': 'New Stage', 'sequence': 1})
        (test_event_1 | test_event_2).stage_id = new_stage.id  # Change event stage

        self.assertEqual(test_event_1.kanban_state, 'normal', 'kanban state should reset to "normal" on stage change')
        self.assertEqual(test_event_2.kanban_state, 'cancel', 'kanban state should not reset on stage change')

    @freeze_time('2021-12-01 11:00:00')
    @users('event_user')
    def test_event_seats_and_schedulers(self):
        test_event = self.env['event.event'].browse(self.test_event.ids)
        ticket_1 = test_event.event_ticket_ids.filtered(lambda ticket: ticket.name == 'Ticket1')
        ticket_2 = test_event.event_ticket_ids.filtered(lambda ticket: ticket.name == 'Ticket2')

        # check initial data
        self.assertTrue(test_event.event_registrations_started)
        self.assertEqual(test_event.seats_available, 30)
        self.assertEqual(ticket_1.seats_available, 10)
        self.assertTrue(ticket_1.sale_available)
        self.assertEqual(ticket_2.seats_available, 0)
        self.assertFalse(ticket_2.sale_available)

        # make 9 registrations (let 1 on ticket)
        with self.mock_datetime_and_now(self.reference_now), \
             self.mock_mail_gateway():
            self.env['event.registration'].create([
                {
                     'email': 'test.customer.%02d@test.example.com' % x,
                     'phone': '04560011%02d' % x,
                     'event_id': test_event.id,
                     'event_ticket_id': ticket_1.id,
                     'name': 'Customer %d' % x,
                }
                for x in range(0, 9)
            ])
        # generated emails from scheduler
        self.assertEqual(len(self._new_mails), 9)
        # event and ticket seats update
        self.assertEqual(len(test_event.registration_ids), 9)
        self.assertEqual(test_event.seats_available, 21)
        self.assertEqual(ticket_1.seats_available, 1)
        self.assertEqual(ticket_2.seats_available, 0)

        # prevent registration due to ticket limit
        with self.mock_datetime_and_now(self.reference_now), \
             self.assertRaises(exceptions.ValidationError):
            self.env['event.registration'].create([
                {
                     'email': 'additional.customer.%02d@test.example.com' % x,
                     'phone': '04560011%02d' % x,
                     'event_id': test_event.id,
                     'event_ticket_id': ticket_1.id,
                     'name': 'Additional Customer %d' % x,
                }
                for x in range(0, 2)
            ])

        # make 20 registrations (on free ticket)
        with self.mock_datetime_and_now(self.reference_now), \
             self.mock_mail_gateway():
            self.env['event.registration'].create([
                {
                     'email': 'other.customer.%02d@test.example.com' % x,
                     'phone': '04560011%02d' % x,
                     'event_id': test_event.id,
                     'event_ticket_id': ticket_2.id,
                     'name': 'Other Customer %d' % x,
                }
                for x in range(0, 20)
            ])
        # event and ticket seats update
        self.assertEqual(len(test_event.registration_ids), 29)
        self.assertEqual(test_event.seats_available, 1)
        self.assertEqual(ticket_1.seats_available, 1)
        self.assertEqual(ticket_2.seats_available, 0)

        # prevent registration due to event limit
        with self.mock_datetime_and_now(self.reference_now), \
             self.assertRaises(exceptions.ValidationError):
            self.env['event.registration'].create([
                {
                     'email': 'additional.customer.%02d@test.example.com' % x,
                     'phone': '04560011%02d' % x,
                     'event_id': test_event.id,
                     'event_ticket_id': ticket_2.id,
                     'name': 'Additional Customer %d' % x,
                }
                for x in range(0, 2)
            ])
