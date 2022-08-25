# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import TransactionCase, new_test_user


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
