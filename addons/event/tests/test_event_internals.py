# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo import Command
from odoo.addons.event.tests.common import EventCase
from odoo import exceptions
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users, Form, tagged
from odoo.tools import mute_logger


class TestEventInternalsCommon(EventCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventInternalsCommon, cls).setUpClass()

        cls.event_type_complex = cls.env['event.type'].create({
            'name': 'Update Type',
            'has_seats_limitation': True,
            'seats_max': 30,
            'default_timezone': 'Europe/Paris',
            'event_type_ticket_ids': [
                (0, 0, {'name': 'First Ticket',}),
                (0, 0, {'name': 'Second Ticket',}),
            ],
            'event_type_mail_ids': [
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_ref': 'mail.template,%i' % cls.env['ir.model.data']._xmlid_to_res_id('event.event_subscription')}),
                (0, 0, {  # 1 days before event
                    'interval_nbr': 1,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'template_ref': 'mail.template,%i' % cls.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')}),
            ],
        })

        # Mock dates to have reproducible computed fields based on time
        cls.reference_now = datetime(2020, 1, 31, 10, 0, 0)
        cls.reference_beg = datetime(2020, 2, 1, 8, 30, 0)
        cls.reference_end = datetime(2020, 2, 4, 18, 45, 0)

        cls.event_0 = cls.env['event.event'].create({
            'date_begin': cls.reference_beg,
            'date_end': cls.reference_end,
            'date_tz': 'Europe/Brussels',
            'name': 'TestEvent',
        })


@tagged('event_event')
class TestEventData(TestEventInternalsCommon):

    @users('user_eventmanager')
    def test_event_date_computation(self):
        event = self.event_0.with_user(self.env.user)
        with freeze_time(self.reference_now):
            event.write({
                'registration_ids': [(0, 0, {'partner_id': self.event_customer.id, 'name': 'test_reg'})],
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
            self.assertEqual(registration.get_date_range_str(), u'on Mar 1, 2020')

            # Is actually 8:30 to 20:00 in Mexico
            event.write({
                'date_begin': datetime(2020, 1, 31, 14, 30, 0),
                'date_end': datetime(2020, 2, 1, 2, 0, 0),
                'date_tz': 'Mexico/General'
            })
            self.assertTrue(event.is_one_day)

    @freeze_time('2020-1-31 10:00:00')
    @users('user_eventmanager')
    def test_event_date_timezone(self):
        event = self.event_0.with_user(self.env.user)
        # Is actually 8:30 to 20:00 in Mexico
        event.write({
            'date_begin': datetime(2020, 1, 31, 14, 30, 0),
            'date_end': datetime(2020, 2, 1, 2, 0, 0),
            'date_tz': 'Mexico/General'
        })
        self.assertTrue(event.is_one_day)
        self.assertFalse(event.is_ongoing)

    @users('user_eventmanager')
    @mute_logger('odoo.models.unlink')
    def test_event_configuration_from_type(self):
        """ Test data computation of event coming from its event.type template. """
        self.assertEqual(self.env.user.tz, 'Europe/Brussels')

        # ------------------------------------------------------------
        # STARTING DATA
        # ------------------------------------------------------------

        event_type = self.env['event.type'].browse(self.event_type_complex.id)

        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
            'event_mail_ids': False,
        })
        self.assertEqual(event.date_tz, self.env.user.tz)
        self.assertFalse(event.seats_limited)
        self.assertEqual(event.event_mail_ids, self.env['event.mail'])
        self.assertEqual(event.event_ticket_ids, self.env['event.event.ticket'])

        registration = self._create_registrations(event, 1)

        # ------------------------------------------------------------
        # FILL SYNC TEST
        # ------------------------------------------------------------

        # change template to a one with mails -> fill event as it is void
        event_type.write({
            'event_type_mail_ids': [(5, 0), (0, 0, {
                'interval_nbr': 1, 'interval_unit': 'days', 'interval_type': 'before_event',
                'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')})
            ],
            'event_type_ticket_ids': [(5, 0), (0, 0, {'name': 'TestRegistration'})],
        })
        event.write({'event_type_id': event_type.id})
        self.assertEqual(event.date_tz, 'Europe/Paris')
        self.assertTrue(event.seats_limited)
        self.assertEqual(event.seats_max, event_type.seats_max)
        # check 2many fields being populated
        self.assertEqual(len(event.event_mail_ids), 1)
        self.assertEqual(event.event_mail_ids.interval_nbr, 1)
        self.assertEqual(event.event_mail_ids.interval_unit, 'days')
        self.assertEqual(event.event_mail_ids.interval_type, 'before_event')
        self.assertEqual(event.event_mail_ids.template_ref, self.env.ref('event.event_reminder'))
        self.assertEqual(len(event.event_ticket_ids), 1)

        # update template, unlink from event -> should not impact event
        event_type.write({'has_seats_limitation': False})
        self.assertEqual(event_type.seats_max, 0)
        self.assertTrue(event.seats_limited)
        self.assertEqual(event.seats_max, 30)  # original template value
        event.write({'event_type_id': False})
        self.assertEqual(event.event_type_id, self.env["event.type"])

        # set template back -> update event
        event.write({'event_type_id': event_type.id})
        self.assertFalse(event.seats_limited)
        self.assertEqual(event.seats_max, 0)
        self.assertEqual(len(event.event_ticket_ids), 1)
        event_ticket1 = event.event_ticket_ids[0]
        self.assertEqual(event_ticket1.name, 'TestRegistration')

    @users('user_eventmanager')
    def test_event_configuration_mails_from_type(self):
        """ Test data computation (related to mails) of event coming from its event.type template.
        This test uses pretty low level Form data checks, as manipulations in a non-saved Form are
        required to highlight an undesired behavior when switching event_type templates :
        event_mail_ids not linked to a registration were generated and kept when switching between
        different templates in the Form, which could rapidly lead to a substantial amount of
        undesired lines. """
        # setup test records
        event_type_default = self.env['event.type'].create({
            'name': 'Type Default',
            'event_type_mail_ids': False,
        })
        event_type_mails = self.env['event.type'].create({
            'name': 'Type Mails',
            'event_type_mail_ids': [
                Command.clear(),
                Command.create({
                    'notification_type': 'mail',
                    'interval_nbr': 77,
                    'interval_unit': 'days',
                    'interval_type': 'after_event',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder'),
                })
            ],
        })
        event = self.env['event.event'].create({
            'name': 'Event',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
            'event_type_id': event_type_default.id
        })
        event.write({
            'event_mail_ids': [
                Command.clear(),
                Command.create({
                    'notification_type': 'mail',
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription'),
                })
            ]
        })
        mail = event.event_mail_ids[0]
        registration = self._create_registrations(event, 1)
        self.assertEqual(registration.state, 'open')
        # verify that mail is linked to the registration
        self.assertEqual(
            set(mail.mapped('mail_registration_ids.registration_id.id')),
            set([registration.id])
        )
        # start test scenario
        event_form = Form(event)
        # verify that mail is linked to the event in the form
        self.assertEqual(
            set(map(lambda m: m.get('id', None), event_form.event_mail_ids._records)),
            set([mail.id])
        )
        # switch to an event_type with a mail template which should be computed
        event_form.event_type_id = event_type_mails
        # verify that 2 mails were computed
        self.assertEqual(len(event_form.event_mail_ids._records), 2)
        # verify that the mail linked to the registration was kept
        self.assertTrue(filter(lambda m: m.get('id', None) == mail.id, event_form.event_mail_ids._records))
        # since the other computed event.mail is to be created from an event.type.mail template,
        # verify that its attributes are the correct ones
        computed_mail = next(filter(lambda m: m.get('id', None) != mail.id, event_form.event_mail_ids._records), {})
        self.assertEqual(computed_mail.get('interval_nbr', None), 77)
        self.assertEqual(computed_mail.get('interval_unit', None), 'days')
        self.assertEqual(computed_mail.get('interval_type', None), 'after_event')
        # switch back to an event type without a mail template
        event_form.event_type_id = event_type_default
        # verify that the mail linked to the registration was kept, and the other removed
        self.assertEqual(
            set(map(lambda m: m.get('id', None), event_form.event_mail_ids._records)),
            set([mail.id])
        )

    @users('user_eventmanager')
    def test_event_configuration_note_from_type(self):
        event_type = self.env['event.type'].browse(self.event_type_complex.id)

        event = self.env['event.event'].create({
            'name': 'Event Update Type Note',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })

        # verify that note is not propagated if the event type contains blank html
        event.write({'note': '<p>Event Note</p>'})
        event_type.write({'note': '<p><br></p>'})
        event.write({'event_type_id': event_type.id})
        self.assertEqual(event.note, '<p>Event Note</p>')

        # verify that note is correctly propagated if it contains non empty html
        event.write({'event_type_id': False})
        event_type.write({'note': '<p>Event Type Note</p>'})
        event.write({'event_type_id': event_type.id})
        self.assertEqual(event.note, '<p>Event Type Note</p>')

    @users('user_eventmanager')
    def test_event_configuration_tickets_from_type(self):
        """ Test data computation (related to tickets) of event coming from its event.type template.
        This test uses pretty low level Form data checks, as manipulations in a non-saved Form are
        required to highlight an undesired behavior when switching event_type templates :
        event_ticket_ids not linked to a registration were generated and kept when switching between
        different templates in the Form, which could rapidly lead to a substantial amount of
        undesired lines. """
        # setup test records
        event_type_default = self.env['event.type'].create({
            'name': 'Type Default',
        })
        event_type_tickets = self.env['event.type'].create({
            'name': 'Type Tickets',
        })
        event_type_tickets.write({
            'event_type_ticket_ids': [
                Command.clear(),
                Command.create({
                    'name': 'Default Ticket',
                    'seats_max': 10,
                })
            ]
        })
        event = self.env['event.event'].create({
            'name': 'Event',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
            'event_type_id': event_type_default.id
        })
        event.write({
            'event_ticket_ids': [
                Command.clear(),
                Command.create({
                    'name': 'Registration Ticket',
                    'seats_max': 10,
                })
            ]
        })
        ticket = event.event_ticket_ids[0]
        registration = self._create_registrations(event, 1)
        # link the ticket to the registration
        registration.write({'event_ticket_id': ticket.id})
        # start test scenario
        event_form = Form(event)
        # verify that the ticket is linked to the event in the form
        self.assertEqual(
            set(map(lambda m: m.get('name', None), event_form.event_ticket_ids._records)),
            set(['Registration Ticket'])
        )
        # switch to an event_type with a ticket template which should be computed
        event_form.event_type_id = event_type_tickets
        # verify that both tickets are computed
        self.assertEqual(
            set(map(lambda m: m.get('name', None), event_form.event_ticket_ids._records)),
            set(['Registration Ticket', 'Default Ticket'])
        )
        # switch back to an event_type without default tickets
        event_form.event_type_id = event_type_default
        # verify that the ticket linked to the registration was kept, and the other removed
        self.assertEqual(
            set(map(lambda m: m.get('name', None), event_form.event_ticket_ids._records)),
            set(['Registration Ticket'])
        )

    @users('user_eventmanager')
    def test_event_mail_default_config(self):
        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })
        self.assertEqual(event.date_tz, self.env.user.tz)
        self.assertFalse(event.seats_limited)

        #Event Communications: when no event type, default configuration
        self.assertEqual(len(event.event_mail_ids), 3)
        self.assertEqual(event.event_mail_ids[0].interval_unit, 'now')
        self.assertEqual(event.event_mail_ids[0].interval_type, 'after_sub')
        self.assertEqual(event.event_mail_ids[0].template_ref, self.env.ref('event.event_subscription'))
        self.assertEqual(event.event_mail_ids[1].interval_nbr, 1)
        self.assertEqual(event.event_mail_ids[1].interval_unit, 'hours')
        self.assertEqual(event.event_mail_ids[1].interval_type, 'before_event')
        self.assertEqual(event.event_mail_ids[1].template_ref, self.env.ref('event.event_reminder'))
        self.assertEqual(event.event_mail_ids[2].interval_nbr, 3)
        self.assertEqual(event.event_mail_ids[2].interval_unit, 'days')
        self.assertEqual(event.event_mail_ids[2].interval_type, 'before_event')
        self.assertEqual(event.event_mail_ids[2].template_ref, self.env.ref('event.event_reminder'))

        event.write({
            'event_mail_ids': False
        })
        self.assertEqual(event.event_mail_ids, self.env['event.mail'])

    def test_event_mail_filter_template_on_event(self):
        """Test that the mail template are filtered to show only those which are related to the event registration model.

        This is important to be able to show only relevant mail templates on the related
        field "template_ref".
        """
        self.env['mail.template'].search([('model', '=', 'event.registration')]).unlink()
        self.env['mail.template'].create({'model_id': self.env['ir.model']._get('event.registration').id, 'name': 'test template'})
        self.env['mail.template'].create({'model_id': self.env['ir.model']._get('res.partner').id, 'name': 'test template'})
        templates = self.env['mail.template'].with_context(filter_template_on_event=True).name_search('test template')
        self.assertEqual(len(templates), 1, 'Should return only mail templates related to the event registration model')

    @freeze_time('2020-1-31 10:00:00')
    @users('user_eventmanager')
    def test_event_registrable(self):
        """Test if `_compute_event_registrations_open` works properly."""
        event = self.event_0.with_user(self.env.user)
        event.write({
            'date_begin': datetime(2020, 1, 30, 8, 0, 0),
            'date_end': datetime(2020, 1, 31, 8, 0, 0),
        })
        self.assertFalse(event.event_registrations_open)
        event.write({
            'date_end': datetime(2020, 2, 4, 8, 0, 0),
        })
        self.assertTrue(event.event_registrations_open)

        # ticket without dates boundaries -> ok
        ticket = self.env['event.event.ticket'].create({
            'name': 'TestTicket',
            'event_id': event.id,
        })
        self.assertTrue(event.event_registrations_open)

        # even with valid tickets, date limits registrations
        event.write({
            'date_begin': datetime(2020, 1, 28, 15, 0, 0),
            'date_end': datetime(2020, 1, 30, 15, 0, 0),
        })
        self.assertFalse(event.event_registrations_open)

        # no more seats available
        registration = self.env['event.registration'].create({
            'name': 'Albert Test',
            'event_id': event.id,
        })
        event.write({
            'date_end': datetime(2020, 2, 1, 15, 0, 0),
            'seats_max': 1,
            'seats_limited': True,
        })
        self.assertEqual(event.seats_available, 0)
        self.assertFalse(event.event_registrations_open)

        # seats available are back
        registration.unlink()
        self.assertEqual(event.seats_available, 1)
        self.assertTrue(event.event_registrations_open)

        # but tickets are expired
        ticket.write({'end_sale_datetime': datetime(2020, 1, 30, 15, 0, 0)})
        self.assertTrue(ticket.is_expired)
        self.assertFalse(event.event_registrations_open)

    @freeze_time('2020-1-31 10:00:00')
    @users('user_eventmanager')
    def test_event_ongoing(self):
        event_1 = self.env['event.event'].create({
            'name': 'Test Event 1',
            'date_begin': datetime(2020, 1, 25, 8, 0, 0),
            'date_end': datetime(2020, 2, 1, 18, 0, 0),
        })
        self.assertTrue(event_1.is_ongoing)
        ongoing_events = self.env['event.event'].search([('is_ongoing', '=', True)])
        self.assertIn(event_1, ongoing_events)

        event_1.update({'date_begin': datetime(2020, 2, 1, 9, 0, 0)})
        self.assertFalse(event_1.is_ongoing)
        ongoing_events = self.env['event.event'].search([('is_ongoing', '=', True)])
        self.assertNotIn(event_1, ongoing_events)

        event_2 = self.env['event.event'].create({
            'name': 'Test Event 2',
            'date_begin': datetime(2020, 1, 25, 8, 0, 0),
            'date_end': datetime(2020, 1, 28, 8, 0, 0),
        })
        self.assertFalse(event_2.is_ongoing)
        finished_or_upcoming_events = self.env['event.event'].search([('is_ongoing', '=', False)])
        self.assertIn(event_2, finished_or_upcoming_events)

        event_2.update({'date_end': datetime(2020, 2, 2, 8, 0, 1)})
        self.assertTrue(event_2.is_ongoing)
        finished_or_upcoming_events = self.env['event.event'].search([('is_ongoing', '=', False)])
        self.assertNotIn(event_2, finished_or_upcoming_events)

    @users('user_eventmanager')
    def test_event_seats(self):
        event_type = self.event_type_complex.with_user(self.env.user)
        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'event_type_id': event_type.id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })

        self.assertEqual(event.address_id, self.env.user.company_id.partner_id)
        # seats: coming from event type configuration
        self.assertTrue(event.seats_limited)
        self.assertEqual(event.seats_available, event.event_type_id.seats_max)
        self.assertEqual(event.seats_reserved, 0)
        self.assertEqual(event.seats_used, 0)
        self.assertEqual(event.seats_taken, 0)

        # create registration in order to check the seats computation
        reg_open_multiple = self.env['event.registration'].create([{
            'event_id': event.id,
            'name': 'reg_open',
        } for _ in range(5)])
        self.assertEqual(set(reg_open_multiple.mapped('state')), {'open'})
        reg_open = reg_open_multiple[0]

        reg_draft = self.env['event.registration'].create({
            'event_id': event.id,
            'name': 'reg_draft',
        })
        reg_draft.write({'state': 'draft'})
        reg_done = self.env['event.registration'].create({
            'event_id': event.id,
            'name': 'reg_done',
        })
        reg_done.write({'state': 'done'})
        self.assertEqual(event.seats_available, event.event_type_id.seats_max - 6)
        self.assertEqual(event.seats_reserved, 5)
        self.assertEqual(event.seats_used, 1)
        self.assertEqual(event.seats_taken, 6)

        # ------------------------------------------------------------
        # SEATS AVAILABILITY AND (UN-)ARCHIVING REGISTRATIONS
        # ------------------------------------------------------------

        # Archiving and seats availability
        reg_open.action_archive()
        self.assertEqual(event.seats_reserved, 4)
        self.assertEqual(event.seats_available, event.event_type_id.seats_max - 5)
        self.assertEqual(event.seats_taken, 5)

        reg_draft.action_archive()
        self.assertEqual(event.seats_available, event.event_type_id.seats_max - 5)
        self.assertEqual(event.seats_taken, 5)

        # Un-archiving confirmed seats requires available seat(s)
        reg_open.action_unarchive()
        self.assertEqual(event.seats_reserved, 5)
        self.assertEqual(event.seats_available, event.event_type_id.seats_max - 6)
        self.assertEqual(event.seats_taken, 6)

        reg_draft.action_unarchive()
        self.assertEqual(event.seats_available, event.event_type_id.seats_max - 6)
        self.assertEqual(event.seats_taken, 6)

        reg_open.action_archive()
        self.assertEqual(event.seats_reserved, 4)

        # It is not possible to set a seats_max value below number of current
        # confirmed registrations. (4 "reserved" + 1 "used")
        with self.assertRaises(exceptions.ValidationError):
            event.write({'seats_max': 4})
        event.write({'seats_max': 5})
        self.assertEqual(event.seats_available, 0)

        # It is not possible to unarchive a confirmed seat if the event is fully booked
        with self.assertRaises(exceptions.ValidationError):
            reg_open.action_unarchive()

        # raising the limit allows it
        event.write({'seats_max': 6})
        self.assertEqual(reg_open.state, "open")
        reg_open.action_unarchive()

        # It is not possible to confirm a draft reservation if the event is
        # fully booked
        with self.assertRaises(exceptions.ValidationError):
            reg_draft.write({'state': 'open'})

        # It is not possible to create an open registration (default value)
        # when the event is full
        new_open_registration = {
            'event_id': event.id,
            'name': 'reg_open',
        }
        with self.assertRaises(exceptions.ValidationError):
            self.env['event.registration'].create(new_open_registration)

        # If the seats limitation is removed, it becomes possible of course
        event.write({'seats_limited': 0})
        self.env['event.registration'].create(new_open_registration)
        reg_draft.write({'state': 'open'})


@tagged('event_registration')
class TestEventRegistrationData(TestEventInternalsCommon):

    @users('user_eventmanager')
    def test_registration_partner_sync(self):
        """ Test registration computed fields about partner """
        test_email = '"Nibbler In Space" <nibbler@futurama.example.com>'
        test_phone = '0456001122'
        test_phone_fmt = '+32456001122'

        event = self.env['event.event'].browse(self.event_0.ids)
        customer = self.env['res.partner'].browse(self.event_customer.id)

        # take all from partner
        event.write({
            'registration_ids': [(0, 0, {
                'partner_id': customer.id,
            })]
        })
        new_reg = event.registration_ids[0]
        self.assertEqual(new_reg.partner_id, customer)
        self.assertEqual(new_reg.name, customer.name)
        self.assertEqual(new_reg.email, customer.email)
        self.assertEqual(new_reg.phone, customer.phone)

        # partial update
        event.write({
            'registration_ids': [(0, 0, {
                'partner_id': customer.id,
                'name': 'Nibbler In Space',
                'email': test_email,
            })]
        })
        new_reg = event.registration_ids.sorted()[0]
        self.assertEqual(new_reg.partner_id, customer)
        self.assertEqual(
            new_reg.name, 'Nibbler In Space',
            'Registration should take user input over computed partner value')
        self.assertEqual(
            new_reg.email, test_email,
            'Registration should take user input over computed partner value')
        self.assertEqual(
            new_reg.phone, customer.phone,
            'Registration should take partner value if not user input')

        # already filled information should not be updated
        event.write({
            'registration_ids': [(0, 0, {
                'name': 'Nibbler In Space',
                'phone': test_phone,
            })]
        })
        new_reg = event.registration_ids.sorted()[0]
        self.assertEqual(new_reg.name, 'Nibbler In Space')
        self.assertEqual(new_reg.email, False)
        self.assertEqual(new_reg.phone, test_phone_fmt)
        new_reg.write({'partner_id': customer.id})
        self.assertEqual(new_reg.partner_id, customer)
        self.assertEqual(new_reg.name, 'Nibbler In Space')
        self.assertEqual(new_reg.email, customer.email)
        self.assertEqual(new_reg.phone, test_phone_fmt)

    @users('user_eventmanager')
    def test_registration_partner_sync_company(self):
        """ Test synchronization involving companies """
        event = self.env['event.event'].browse(self.event_0.ids)
        customer = self.env['res.partner'].browse(self.event_customer.id)

        # create company structure (using sudo as required partner manager group)
        company = self.env['res.partner'].sudo().create({
            'name': 'Customer Company',
            'is_company': True,
            'type': 'other',
        })
        customer.sudo().write({'type': 'invoice', 'parent_id': company.id})
        contact = self.env['res.partner'].sudo().create({
            'name': 'ContactName',
            'parent_id': company.id,
            'type': 'contact',
            'email': 'ContactEmail <contact.email@test.example.com>',
            'phone': '+32456998877',
        })

        # take all from partner
        event.write({
            'registration_ids': [(0, 0, {
                'partner_id': customer.id,
            })]
        })
        new_reg = event.registration_ids[0]
        self.assertEqual(new_reg.partner_id, customer)
        self.assertEqual(new_reg.name, contact.name)
        self.assertEqual(new_reg.email, contact.email)
        self.assertEqual(new_reg.phone, contact.phone)


@tagged('event_registration', 'phone_number')
class TestEventRegistrationPhone(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_event_address = cls.env['res.partner'].create({
            'city': 'Gandhinagar',
            'country_id': cls.env.ref("base.in").id,
            'name': 'Odoo In',
            'zip': '382007',
        })
        cls.test_event = cls.env['event.event'].create({
            'address_id': cls.test_event_address.id,
            'company_id': cls.company_admin.id,
            'date_begin': datetime(2023, 6, 5, 8, 0, 0),
            'date_end': datetime(2023, 6, 8, 18, 0, 0),
            'name': 'Test Phone Format',
        })

    @users('user_eventregistrationdesk')
    def test_assert_initial_values(self):
        customer = self.event_customer.with_env(self.env)
        customer2 = self.event_customer2.with_env(self.env)
        event = self.test_event.with_env(self.env)

        self.assertFalse(customer.mobile)
        self.assertEqual(customer.phone, '0485112233')
        self.assertEqual(customer2.mobile, '0456654321')
        self.assertEqual(customer2.phone, '0456987654')

        self.assertEqual(event.company_id.country_id, self.env.ref("base.be"))
        self.assertEqual(event.country_id, self.env.ref("base.in"))

    @users('user_eventregistrationdesk')
    def test_registration_form_phone(self):
        """ Test onchange on phone / mobile, should try to format number """
        event = self.test_event.with_user(self.env.user)

        reg_form = Form(self.env['event.registration'])
        reg_form.event_id = event
        reg_form.phone = '7200000000'
        self.assertEqual(reg_form.phone, '+917200000000')

    @users('user_eventregistrationdesk')
    def test_registration_phone_format(self):
        """ Test phone formatting: based on partner (BE numbers) or event
        (IN numbers) or company (BE numbers). """
        partner_mobileonly = self.env['res.partner'].sudo().create({
            'name': 'Constantin Customer 3 Mobile',
            'email': 'constantin3test.example.com',
            'country_id': self.env.ref('base.be').id,
            'phone': False,
            'mobile': '0456987654',
            })
        event = self.test_event.with_user(self.env.user)

        # customer_id, phone -> based on partner or event country
        sources = [
            (self.event_customer.id, None),  # BE local on partner
            (self.event_customer2.id, None),  # BE local on partner
            (partner_mobileonly.id, None),  # BE local on partner
            (self.event_customer2.id, '0456001122'),  # BE local + on partner
            (False, '0456778899'),  # BE local
            (False, '7200000000'),  # IN local
            (False, '+917200000088'),  # IN global
        ]
        # expected phone
        expected = [
            '0485112233',  # partner values, no format (phone only)
            '0456987654',  # partner values, no format (both: phone wins)
            '0456987654',  # partner values, no format (mobile only)
            '+32456001122',  # BE on partner
            '0456778899',  # IN on event -> cannot format BE
            '+917200000000',  # IN on event
            '+917200000088',  # already formatted
        ]
        for (partner_id, phone), exp_phone in zip(sources, expected):
            with self.subTest(partner_id=partner_id, phone=phone):
                create_vals = {
                    'event_id': event.id,
                    'partner_id': partner_id,
                }
                if phone is not None:
                    create_vals['phone'] = phone
                reg = self.env['event.registration'].create(create_vals)
                self.assertEqual(reg.phone, exp_phone)

        # no country on event -> based on partner or event company country
        self.test_event.write({'address_id': False})
        expected = [
            '0485112233',  # partner values, no format (phone only)
            '0456987654',  # partner values, no format (both: phone wins)
            '0456987654',  # partner values, no format (mobile only)
            '+32456001122',  # BE on company
            '+32456778899',  # BE on company
            '7200000000',  # BE on company -> cannot format IN
            '+917200000088',  # already formatted
        ]
        for (partner_id, phone), exp_phone in zip(sources, expected):
            with self.subTest(partner_id=partner_id, phone=phone):
                create_vals = {
                    'event_id': event.id,
                    'partner_id': partner_id,
                }
                if phone is not None:
                    create_vals['phone'] = phone
                reg = self.env['event.registration'].create(create_vals)
                self.assertEqual(reg.phone, exp_phone)


@tagged('event_ticket')
class TestEventTicketData(TestEventInternalsCommon):

    @freeze_time('2020-1-31 10:00:00')
    @users('user_eventmanager')
    def test_event_ticket_fields(self):
        """ Test event ticket fields synchronization """
        INITIAL_TICKET_SEATS_MAX = 30
        event = self.event_0.with_user(self.env.user)
        event.write({
            'event_ticket_ids': [
                (5, 0),
                (0, 0, {
                    'name': 'First Ticket',
                    'seats_max': INITIAL_TICKET_SEATS_MAX,
                }), (0, 0, {  # limited in time, available (01/10 (start) < 01/31 (today) < 02/10 (end))
                    'name': 'Second Ticket',
                    'start_sale_datetime': datetime(2020, 1, 10, 0, 0, 0),
                    'end_sale_datetime': datetime(2020, 2, 10, 23, 59, 59),
                })
            ],
        })
        first_ticket = event.event_ticket_ids.filtered(lambda t: t.name == 'First Ticket')
        second_ticket = event.event_ticket_ids.filtered(lambda t: t.name == 'Second Ticket')

        self.assertTrue(first_ticket.seats_limited)
        self.assertTrue(first_ticket.sale_available)
        self.assertFalse(first_ticket.is_expired)

        self.assertFalse(second_ticket.seats_limited)
        self.assertTrue(second_ticket.sale_available)
        self.assertFalse(second_ticket.is_expired)
        # sale is ended
        second_ticket.write({'end_sale_datetime': datetime(2020, 1, 20, 23, 59, 59)})
        self.assertFalse(second_ticket.sale_available)
        self.assertTrue(second_ticket.is_expired)
        # sale has not started
        second_ticket.write({
            'start_sale_datetime': datetime(2020, 2, 10, 0, 0, 0),
            'end_sale_datetime': datetime(2020, 2, 20, 23, 59, 59),
        })
        self.assertFalse(second_ticket.sale_available)
        self.assertFalse(second_ticket.is_expired)
        # sale started today
        second_ticket.write({
            'start_sale_datetime': datetime(2020, 1, 31, 0, 0, 0),
            'end_sale_datetime': datetime(2020, 2, 20, 23, 59, 59),
        })
        self.assertTrue(second_ticket.sale_available)
        self.assertTrue(second_ticket.is_launched)
        self.assertFalse(second_ticket.is_expired)
        # incoherent dates are invalid
        with self.assertRaises(exceptions.UserError):
            second_ticket.write({'end_sale_datetime': datetime(2020, 1, 20, 23, 59, 59)})

        #test if event start/end dates are taking datetime fields (hours, minutes, seconds) into account
        second_ticket.write({'start_sale_datetime': datetime(2020, 1, 31, 11, 0, 0)})
        self.assertFalse(second_ticket.sale_available)
        self.assertFalse(second_ticket.is_launched)

        second_ticket.write({
            'start_sale_datetime': datetime(2020, 1, 31, 7, 0, 0),
            'end_sale_datetime': datetime(2020, 2, 27, 13, 0, 0)
        })

        self.assertTrue(second_ticket.sale_available)
        self.assertTrue(second_ticket.is_launched)
        self.assertFalse(second_ticket.is_expired)

        second_ticket.write({
            'end_sale_datetime': datetime(2020, 1, 31, 9, 0, 0)
        })

        self.assertFalse(second_ticket.sale_available)
        self.assertTrue(second_ticket.is_expired)

        # ------------------------------------------------------------
        # (UN -)ARCHIVING REGISTRATIONS AND SEATS AVAILABILITY
        # ------------------------------------------------------------

        # Archiving and seats availability
        reg_draft_multiple = self.env['event.registration'].create([{
            'event_id': event.id,
            'name': f'reg_draft #{idx}',
            'event_ticket_id': first_ticket.id,
        } for idx in range(3)])
        # Draft registrations should not impact seats
        reg_draft_multiple.state = 'draft'
        reg_draft = reg_draft_multiple[0]

        reg_open = self.env['event.registration'].create({
            'event_id': event.id,
            'name': 'reg_open',
            'event_ticket_id': first_ticket.id,
        })

        reg_done = self.env['event.registration'].create({
            'event_id': event.id,
            'name': 'reg_done',
            'event_ticket_id': first_ticket.id,
        })
        reg_done.action_set_done()

        self.assertEqual(first_ticket.seats_reserved, 1)
        self.assertEqual(first_ticket.seats_used, 1)
        self.assertEqual(first_ticket.seats_available, INITIAL_TICKET_SEATS_MAX - 2)

        reg_done.action_archive()
        self.assertEqual(first_ticket.seats_used, 0)
        self.assertEqual(first_ticket.seats_available, INITIAL_TICKET_SEATS_MAX - 1)

        reg_open.action_archive()
        self.assertEqual(first_ticket.seats_reserved, 0)
        self.assertEqual(first_ticket.seats_available, INITIAL_TICKET_SEATS_MAX)

        # Un-archiving confirmed/done seats requires available seat(s)
        reg_open.action_unarchive()
        self.assertEqual(first_ticket.seats_reserved, 1)
        self.assertEqual(first_ticket.seats_available, INITIAL_TICKET_SEATS_MAX - 1)

        reg_done.action_unarchive()
        self.assertEqual(first_ticket.seats_used, 1)
        self.assertEqual(first_ticket.seats_available, INITIAL_TICKET_SEATS_MAX - 2)

        # It is not possible to set a seats_max value below the current number of confirmed
        # registrations. (There is still 1 "used" seat too)
        with self.assertRaises(exceptions.ValidationError):
            first_ticket.write({'seats_max': 1})

        reg_open.action_archive()
        first_ticket.write({'seats_max': 1})

        # It is not possible to unarchive confirmed seat if ticket is fully booked
        with self.assertRaises(exceptions.ValidationError):
            reg_open.action_unarchive()

        # SEATS AVAILABILITY

        # It is impossible to create an open registration when the
        # ticket is fully booked (1 used + 1 reserved)
        self.assertEqual(event.seats_available, 0)
        with self.assertRaises(exceptions.ValidationError):
            self.env['event.registration'].create({
                'event_id': event.id,
                'name': 'New registration with auto confirm',
                'event_ticket_id': first_ticket.id,
            })

        # It is not possible to convert a draft to an open registration
        # when the event is fully booked
        with self.assertRaises(exceptions.ValidationError):
            reg_draft.write({'state': 'open'})


@tagged('event_event')
class TestEventTypeData(TestEventInternalsCommon):

    @users('user_eventmanager')
    def test_event_type_fields(self):
        """ Test event type fields synchronization """
        # create test type and ensure its initial values
        event_type = self.env['event.type'].create({
            'name': 'Testing fields computation',
            'has_seats_limitation': True,
            'seats_max': 30,
        })
        self.assertTrue(event_type.has_seats_limitation)
        self.assertEqual(event_type.seats_max, 30)

        # reset seats limitation
        event_type.write({'has_seats_limitation': False})
        self.assertFalse(event_type.has_seats_limitation)
        self.assertEqual(event_type.seats_max, 0)
