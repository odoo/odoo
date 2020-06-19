# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import SavepointCase, new_test_user
from odoo.exceptions import AccessError


class TestAccessRights(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.john = new_test_user(cls.env, login='john', groups='base.group_user')
        cls.raoul = new_test_user(cls.env, login='raoul', groups='base.group_user')
        cls.portal = new_test_user(cls.env, login='pot', groups='base.group_portal')

    def create_event(self, user, **values):
        return self.env['calendar.event'].with_user(user).create(dict({
            'name': 'Event',
            'start': datetime(2020, 2, 2, 8, 0),
            'stop': datetime(2020, 2, 2, 18, 0),
            'user_id': user.id,
        }, **values))

    def read_event(self, user, events, field):
        data = events.with_user(user).read([field])
        if len(events) == 1:
            return data[0][field]
        mapped_data = {record['id']: record for record in data}
        # Keep the same order
        return [mapped_data[eid][field] for eid in events.ids]

    def test_private_read_name(self):
        event = self.create_event(
            self.john,
            privacy='private',
            name='my private event',
        )
        self.assertEqual(self.read_event(self.john, event, 'name'), 'my private event', "Owner should be able to read the event")
        self.assertEqual(self.read_event(self.raoul, event, 'name'), 'Busy', "Private value should be obfuscated")
        with self.assertRaises(AccessError):
            self.read_event(self.portal, event, 'name')

    def test_private_other_field(self):
        event = self.create_event(
            self.john,
            privacy='private',
            location='in the Sky',
        )
        self.assertEqual(self.read_event(self.john, event, 'location'), 'in the Sky', "Owner should be able to read the event")
        self.assertEqual(self.read_event(self.raoul, event, 'location'), False, "Private value should be obfuscated")
        with self.assertRaises(AccessError):
            self.read_event(self.portal, event, 'location')

    def test_private_and_public(self):
        private = self.create_event(
            self.john,
            privacy='private',
            location='in the Sky',
        )
        public = self.create_event(
            self.john,
            privacy='public',
            location='In Hell',
        )
        [private_location, public_location] = self.read_event(self.raoul, private + public, 'location')
        self.assertEqual(private_location, False, "Private value should be obfuscated")
        self.assertEqual(public_location, 'In Hell', "Public value should not be obfuscated")

    def test_read_group_public(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['start'], groupby='start')
        self.assertTrue(data, "It should be able to read group")

    def test_read_group_private(self):
        event = self.create_event(self.john)
        with self.assertRaises(AccessError):
            self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['name'], groupby='name')

    def test_read_group_agg(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['start'], groupby='start:week')
        self.assertTrue(data, "It should be able to read group")

    def test_read_group_list(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['start'], groupby=['start'])
        self.assertTrue(data, "It should be able to read group")
