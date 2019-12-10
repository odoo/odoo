# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import SavepointCase, new_test_user


class TestEventNotifications(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['calendar.event'].create({
            'name': "Doom's day",
            'start': datetime(2019, 10, 25, 8, 0),
            'stop': datetime(2019, 10, 27, 18, 0),
        }).with_context(mail_notrack=True)
        cls.user = new_test_user(cls.env, 'xav', email='em@il.com', notification_type='inbox')
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
