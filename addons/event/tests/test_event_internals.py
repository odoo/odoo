# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from unittest.mock import patch

from odoo.addons.event.tests.common import TestEventCommon
from odoo import exceptions
from odoo.fields import Datetime as FieldsDatetime, Date as FieldsDate
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestEventData(TestEventCommon):

    @users('user_eventmanager')
    def test_event_date_computation(self):
        self.patcher = patch('odoo.addons.event.models.event_event.fields.Datetime', wraps=FieldsDatetime)
        self.mock_datetime = self.patcher.start()
        self.mock_datetime.now.return_value = datetime(2020, 1, 31, 8, 0, 0)

        event = self.event_0.with_user(self.env.user)
        event.write({
            'registration_ids': [(0, 0, {'partner_id': self.customer.id})],
            'date_begin': datetime(2020, 1, 31, 15, 0, 0),
            'date_end': datetime(2020, 4, 5, 18, 0, 0),
        })
        registration = event.registration_ids[0]
        self.assertEqual(registration.get_date_range_str(), u'today')

        event.date_begin = datetime(2020, 2, 1, 15, 0, 0)
        self.assertEqual(registration.get_date_range_str(), u'tomorrow')

        event.date_begin = datetime(2020, 2, 2, 6, 0, 0)
        self.assertEqual(registration.get_date_range_str(), u'in 2 days')

        event.date_begin = datetime(2020, 2, 20, 17, 0, 0)
        self.assertEqual(registration.get_date_range_str(), u'next month')

        event.date_begin = datetime(2020, 3, 1, 10, 0, 0)
        self.assertEqual(registration.get_date_range_str(), u'on Mar 1, 2020, 11:00:00 AM')

        event.write({
            'date_begin': '2019-11-09 14:30:00',
            'date_end': '2019-11-10 02:00:00',
            'date_tz': 'Mexico/General'
        })
        self.assertTrue(event.is_one_day)

        self.patcher.stop()

    @users('user_eventmanager')
    def test_event_fields(self):
        event_type = self.event_type_complex.with_user(self.env.user)
        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'event_type_id': event_type.id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })
        event._onchange_type()
        self.assertFalse(event.is_online)
        self.assertEqual(event.address_id, self.env.user.company_id.partner_id)
        # seats: coming from event type configuration
        self.assertEqual(event.seats_availability, 'limited')
        self.assertEqual(event.seats_available, event.event_type_id.default_registration_max)
        self.assertEqual(event.seats_unconfirmed, 0)
        self.assertEqual(event.seats_reserved, 0)
        self.assertEqual(event.seats_used, 0)
        self.assertEqual(event.seats_expected, 0)

        # set is_online: should reset the address_id field
        event.update({'is_online': True})
        event._onchange_is_online()
        self.assertTrue(event.is_online)
        self.assertFalse(event.address_id)

        # create registration in order to check the seats computation
        self.assertTrue(event.auto_confirm)
        for x in range(5):
            reg = self.env['event.registration'].create({
                'event_id': event.id
            })
            self.assertEqual(reg.state, 'open')
        reg_draft = self.env['event.registration'].create({
            'event_id': event.id
        })
        reg_draft.write({'state': 'draft'})
        reg_done = self.env['event.registration'].create({
            'event_id': event.id
        })
        reg_done.write({'state': 'done'})
        self.assertEqual(event.seats_available, event.event_type_id.default_registration_max - 6)
        self.assertEqual(event.seats_unconfirmed, 1)
        self.assertEqual(event.seats_reserved, 5)
        self.assertEqual(event.seats_used, 1)
        self.assertEqual(event.seats_expected, 7)

    @users('user_eventmanager')
    @mute_logger('odoo.models.unlink')
    def test_event_configuration_from_type(self):
        """ Test data computation of event coming from its event.type template.
        Some one2many notably are duplicated from type configuration and some
        advanced testing is required, notably mail schedulers. """

        self.assertEqual(self.env.user.tz, 'Europe/Brussels')

        event_type = self.event_type_complex.with_user(self.env.user)
        event_type.write({
            'use_mail_schedule': False,
        })
        # Event type does not use mail schedule but data is kept for compatibility and avoid recreating them
        self.assertEqual(len(event_type.event_type_mail_ids), 2)

        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
            'auto_confirm': False,
            'twitter_hashtag': 'somuchwow',
            'is_online': True,
        })
        self.assertEqual(event.date_tz, self.env.user.tz)
        self.assertEqual(event.seats_availability, 'unlimited')
        self.assertFalse(event.auto_confirm)
        self.assertEqual(event.twitter_hashtag, 'somuchwow')
        self.assertTrue(event.is_online)
        self.assertEqual(event.event_mail_ids, self.env['event.mail'])

        event.update({'event_type_id': event_type.id})
        event._onchange_type()
        self.assertEqual(event.date_tz, 'Europe/Paris')
        self.assertEqual(event.seats_availability, 'limited')
        self.assertEqual(event.seats_min, event_type.default_registration_min)
        self.assertEqual(event.seats_max, event_type.default_registration_max)
        self.assertTrue(event.auto_confirm)
        self.assertEqual(event.twitter_hashtag, event_type.default_hashtag)
        self.assertFalse(event.is_online)
        self.assertEqual(event.event_mail_ids, self.env['event.mail'])

        event_type.write({
            'use_mail_schedule': True,
            'event_type_mail_ids': [(5, 0), (0, 0, {
                'interval_nbr': 1, 'interval_unit': 'days', 'interval_type': 'before_event',
                'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_reminder')})]
        })
        event._onchange_type()
        self.assertEqual(event.event_mail_ids.interval_nbr, 1)
        self.assertEqual(event.event_mail_ids.interval_unit, 'days')
        self.assertEqual(event.event_mail_ids.interval_type, 'before_event')
        self.assertEqual(event.event_mail_ids.template_id, self.env.ref('event.event_reminder'))

    @users('user_eventmanager')
    def test_event_registrable(self):
        """Test if `_compute_event_registrations_open` works properly."""
        event = self.event_0.with_user(self.env.user)
        self.assertTrue(event.event_registrations_open)

        # ticket without dates boundaries -> ok
        ticket = self.env['event.event.ticket'].create({
            'name': 'TestTicket',
            'event_id': event.id,
        })
        self.assertTrue(event.event_registrations_open)

        # even with valid tickets, date limits registrations
        event.write({
            'date_begin': datetime.now() - timedelta(days=3),
            'date_end': datetime.now() - timedelta(days=1),
        })
        self.assertFalse(event.event_registrations_open)

        # no more seats available
        registration = self.env['event.registration'].create({
            'name': 'Albert Test',
            'event_id': event.id,
        })
        registration.action_confirm()
        event.write({
            'date_end': datetime.now() + timedelta(days=3),
            'seats_max': 1,
            'seats_availability': 'limited',
        })
        self.assertEqual(event.seats_available, 0)
        self.assertFalse(event.event_registrations_open)

        # seats available are back
        registration.unlink()
        self.assertEqual(event.seats_available, 1)
        self.assertTrue(event.event_registrations_open)

        # but tickets are expired
        ticket.write({'end_sale_date': datetime.now() - timedelta(days=2)})
        self.assertTrue(ticket.is_expired)
        self.assertFalse(event.event_registrations_open)


class TestEventTicketData(TestEventCommon):

    def setUp(self):
        super(TestEventTicketData, self).setUp()
        self.ticket_date_patcher = patch('odoo.addons.event.models.event_ticket.fields.Date', wraps=FieldsDate)
        self.ticket_date_patcher_mock = self.ticket_date_patcher.start()
        self.ticket_date_patcher_mock.context_today.return_value = date(2020, 1, 31)

    def tearDown(self):
        super(TestEventTicketData, self).tearDown()
        self.ticket_date_patcher.stop()

    @users('user_eventmanager')
    def test_event_ticket_fields(self):
        """ Test event ticket fields synchronization """
        self.event_type_complex.write({
            'use_ticket': True,
            'event_type_ticket_ids': [
                (5, 0),
                (0, 0, {
                    'name': 'First Ticket',
                    'seats_max': 30,
                }), (0, 0, {  # limited in time, available (01/10 (start) < 01/31 (today) < 02/10 (end))
                    'name': 'Second Ticket',
                    'start_sale_date': date(2020, 1, 10),
                    'end_sale_date': date(2020, 2, 10),
                })
            ],
        })
        first_ticket = self.event_type_complex.event_type_ticket_ids.filtered(lambda t: t.name == 'First Ticket')
        second_ticket = self.event_type_complex.event_type_ticket_ids.filtered(lambda t: t.name == 'Second Ticket')

        self.assertEqual(first_ticket.seats_availability, 'limited')
        self.assertTrue(first_ticket.sale_available)
        self.assertFalse(first_ticket.is_expired)

        self.assertEqual(second_ticket.seats_availability, 'unlimited')
        self.assertTrue(second_ticket.sale_available)
        self.assertFalse(second_ticket.is_expired)
        # sale is ended
        second_ticket.write({'end_sale_date': date(2020, 1, 20)})
        self.assertFalse(second_ticket.sale_available)
        self.assertTrue(second_ticket.is_expired)
        # sale has not started
        second_ticket.write({
            'start_sale_date': date(2020, 2, 10),
            'end_sale_date': date(2020, 2, 20),
        })
        self.assertFalse(second_ticket.sale_available)
        self.assertFalse(second_ticket.is_expired)
        # incoherent dates are invalid
        with self.assertRaises(exceptions.UserError):
            second_ticket.write({'end_sale_date': date(2020, 1, 20)})


class TestEventTypeData(TestEventCommon):

    @users('user_eventmanager')
    def test_event_type_fields(self):
        """ Test event type fields synchronization """
        # create test type and ensure its initial values
        event_type = self.env['event.type'].create({
            'name': 'Testing fields computation',
            'has_seats_limitation': True,
            'default_registration_min': 5,
            'default_registration_max': 30,
            'use_ticket': True,
        })
        event_type._onchange_has_seats_limitation()
        self.assertTrue(event_type.has_seats_limitation)
        self.assertEqual(event_type.default_registration_min, 5)
        self.assertEqual(event_type.default_registration_max, 30)
        self.assertEqual(event_type.event_type_ticket_ids.mapped('name'), ['Registration'])

        # reset seats limitation
        event_type.write({'has_seats_limitation': False})
        event_type._onchange_has_seats_limitation()
        self.assertFalse(event_type.has_seats_limitation)
        self.assertEqual(event_type.default_registration_min, 0)
        self.assertEqual(event_type.default_registration_max, 0)

        # reset tickets
        event_type.write({'use_ticket': False})
        self.assertEqual(event_type.event_type_ticket_ids, self.env['event.type.ticket'])
