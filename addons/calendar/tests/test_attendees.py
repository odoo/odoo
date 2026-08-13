# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase, new_test_user
from odoo.tests import Form
from odoo import fields, Command
from freezegun import freeze_time


class TestEventNotifications(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, 'xav', email='em@il.com', notification_type='inbox')
        cls.event = cls.env['calendar.event'].with_user(cls.user).create({
            'name': "Doom's day",
            'start': datetime(2019, 10, 25, 8, 0),
            'stop': datetime(2019, 10, 27, 18, 0),
        }).with_context(mail_notrack=True)
        cls.partner = cls.user.partner_id

    def test_attendee_added(self):
        self.event.partner_ids = self.partner
        self.assertTrue(self.event.attendee_ids, "It should have created an attendee")
        self.assertEqual(self.event.attendee_ids.partner_id, self.partner, "It should be linked to the partner")
        self.assertIn(self.partner, self.event.message_follower_ids.partner_id, "He should be follower of the event")

    def test_attendee_added_create(self):
        event = self.env['calendar.event'].create({
            'name': "Doom's day",
            'start': datetime(2019, 10, 25, 8, 0),
            'stop': datetime(2019, 10, 27, 18, 0),
            'partner_ids': [(4, self.partner.id)],
        })
        self.assertTrue(event.attendee_ids, "It should have created an attendee")
        self.assertEqual(event.attendee_ids.partner_id, self.partner, "It should be linked to the partner")
        self.assertIn(self.partner, event.message_follower_ids.partner_id, "He should be follower of the event")

    def test_attendee_added_create_with_specific_states(self):
        """
        When an event is created from an external calendar account (such as Google) which is not linked to an
        Odoo account, attendee info such as email and state are given at sync.
        In this case, attendee_ids should be created accordingly.
        """
        organizer_partner = self.env['res.partner'].create({'name': "orga", "email": "orga@google.com"})
        event = self.env['calendar.event'].with_user(self.user).create({
            'name': "Doom's day",
            'start': datetime(2019, 10, 25, 8, 0),
            'stop': datetime(2019, 10, 27, 18, 0),
            'attendee_ids': [
                (0, 0, {'partner_id': self.partner.id, 'state': 'needsAction'}),
                (0, 0, {'partner_id': organizer_partner.id, 'state': 'accepted'})
            ],
            'partner_ids': [(4, self.partner.id), (4, organizer_partner.id)],
        })
        attendees_info = [(a.email, a.state) for a in event.attendee_ids]
        self.assertEqual(len(event.attendee_ids), 2)
        self.assertIn((self.partner.email, "needsAction"), attendees_info)
        self.assertIn((organizer_partner.email, "accepted"), attendees_info)

    def test_attendee_added_multi(self):
        event = self.env['calendar.event'].create({
            'name': "Doom's day",
            'start': datetime(2019, 10, 25, 8, 0),
            'stop': datetime(2019, 10, 27, 18, 0),
        })
        events = self.event | event
        events.partner_ids = self.partner
        self.assertEqual(len(events.attendee_ids), 2, "It should have created one attendee per event")

    def test_attendee_added_write(self):
        """Test that writing ids directly on partner_ids instead of commands is handled."""
        self.event.write({'partner_ids': [self.partner.id]})
        self.assertEqual(self.event.attendee_ids.partner_id, self.partner, "It should be linked to the partner")

    def test_existing_attendee_added(self):
        self.event.partner_ids = self.partner
        attendee = self.event.attendee_ids
        self.event.write({'partner_ids': [(4, self.partner.id)]})  # Add existing partner
        self.assertEqual(self.event.attendee_ids, attendee, "It should not have created an new attendee record")

    def test_attendee_add_self(self):
        self.event.with_user(self.user).partner_ids = self.partner
        self.assertTrue(self.event.attendee_ids, "It should have created an attendee")
        self.assertEqual(self.event.attendee_ids.partner_id, self.partner, "It should be linked to the partner")
        self.assertEqual(self.event.attendee_ids.state, 'accepted', "It should be accepted for the current user")

    def test_attendee_removed(self):
        partner_bis = self.env['res.partner'].create({'name': "Xavier"})
        self.event.partner_ids = partner_bis
        attendee = self.event.attendee_ids
        self.event.partner_ids |= self.partner
        self.event.partner_ids -= self.partner
        self.assertEqual(attendee, self.event.attendee_ids, "It should not have re-created an attendee record")
        self.assertNotIn(self.partner, self.event.attendee_ids.partner_id, "It should have removed the attendee")
        self.assertNotIn(self.partner, self.event.message_follower_ids.partner_id, "It should have unsubscribed the partner")
        self.assertIn(partner_bis, self.event.attendee_ids.partner_id, "It should have left the attendee")

    def test_attendee_without_email(self):
        self.partner.email = False
        self.event.partner_ids = self.partner

        self.assertTrue(self.event.attendee_ids)
        self.assertEqual(self.event.attendee_ids.partner_id, self.partner)
        self.assertTrue(self.event.invalid_email_partner_ids)
        self.assertEqual(self.event.invalid_email_partner_ids, self.partner)

    def test_attendee_with_invalid_email(self):
        self.partner.email = "I'm an invalid email"
        self.event.partner_ids = self.partner

        self.assertTrue(self.event.attendee_ids)
        self.assertEqual(self.event.attendee_ids.partner_id, self.partner)
        self.assertTrue(self.event.invalid_email_partner_ids)
        self.assertEqual(self.event.invalid_email_partner_ids, self.partner)

    def test_default_attendee(self):
        """
        Check if priority list id correctly followed
        1) vals_list[0]['attendee_ids']
        2) vals_list[0]['partner_ids']
        3) context.get('default_attendee_ids')
        """
        partner_bis = self.env['res.partner'].create({'name': "Xavier"})
        event = self.env['calendar.event'].with_user(
            self.user
        ).with_context(
            default_attendee_ids=[(0, 0, {'partner_id': partner_bis.id})]
        ).create({
            'name': "Doom's day",
            'partner_ids': [(4, self.partner.id)],
            'start': datetime(2019, 10, 25, 8, 0),
            'stop': datetime(2019, 10, 27, 18, 0),
        })
        self.assertIn(self.partner, event.attendee_ids.partner_id, "Partner should be in attendee")
        self.assertNotIn(partner_bis, event.attendee_ids.partner_id, "Partner bis should not be in attendee")

    def test_push_meeting_start(self):
        """
        Checks that you can push the start date of an all day meeting.
        """
        attendee = self.env['res.partner'].create({
            'name': "Xavier",
            'email': "xavier@example.com",
            })
        event = self.env['calendar.event'].create({
            'name': "Doom's day",
            'attendee_ids': [Command.create({'partner_id': attendee.id})],
            'allday': True,
            'start_date': fields.Date.today(),
            'stop_date': fields.Date.today(),
        })
        initial_start = event.start
        with Form(event) as event_form:
            event_form.stop_date = datetime.today() + relativedelta(days=1)
            event_form.start_date = datetime.today() + relativedelta(days=1)
        self.assertFalse(initial_start == event.start)

    @freeze_time("2019-10-24 09:00:00", tick=True)
    def test_multi_attendee_mt_note_default(self):
        mt_note = self.env.ref("mail.mt_note")
        mt_note.default = True
        user_exta = new_test_user(self.env, "extra", email="extra@il.com")
        partner_extra = user_exta.partner_id
        event = self.env["calendar.event"].create({
            "name": "Team meeting",
            "attendee_ids": [
                (0, 0, {"partner_id": self.partner.id}),
                (0, 0, {"partner_id": partner_extra.id})
            ],
            "start": datetime(2019, 10, 25, 8, 0),
            "stop": datetime(2019, 10, 25, 10, 0),
        })
        messages = self.env["mail.message"].search([
            ("model", "=", event._name),
            ("res_id", "=", event.id),
            ("message_type", "=", "user_notification")
        ])
        self.assertEqual(len(messages), 2)
        mesage_user = messages.filtered(lambda x: self.partner in x.partner_ids)
        self.assertNotIn(partner_extra, mesage_user.notified_partner_ids)
        mesage_user_extra = messages.filtered(lambda x: partner_extra in x.partner_ids)
        self.assertNotIn(self.partner, mesage_user_extra.notified_partner_ids)
