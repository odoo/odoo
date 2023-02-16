# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TestAccessRights(TransactionCase):

    @classmethod
    @mute_logger('odoo.tests', 'odoo.addons.auth_signup.models.res_users')
    def setUpClass(cls):
        super().setUpClass()
        cls.john = new_test_user(cls.env, login='john', groups='base.group_user')
        cls.raoul = new_test_user(cls.env, login='raoul', groups='base.group_user')
        cls.george = new_test_user(cls.env, login='george', groups='base.group_user')
        cls.portal = new_test_user(cls.env, login='pot', groups='base.group_portal')

    def create_event(self, user, **values):
        return self.env['calendar.event'].with_user(user).create({
            'name': 'Event',
            'start': datetime(2020, 2, 2, 8, 0),
            'stop': datetime(2020, 2, 2, 18, 0),
            'user_id': user.id,
            'partner_ids': [(4, self.george.partner_id.id, 0)],
            **values
        })

    def read_event(self, user, events, field):
        data = events.with_user(user).read([field])
        if len(events) == 1:
            return data[0][field]
        return [r[field] for r in data]

    # don't spam logs with ACL failures from portal
    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_privacy(self):
        event = self.create_event(
            self.john,
            privacy='private',
            name='my private event',
            location='in the Sky'
        )
        for user, field, expect, error in [
            # public field, any employee can read
            (self.john, 'privacy', 'private', None),
            (self.george, 'privacy', 'private', None),
            (self.raoul, 'privacy', 'private', None),
            (self.portal, 'privacy', None, AccessError),
            # substituted private field, only owner and invitees can read, other
            # employees get substitution
            (self.john, 'name', 'my private event', None),
            (self.george, 'name', 'my private event', None),
            (self.raoul, 'name', 'Busy', None),
            (self.portal, 'name', None, AccessError),
            # computed from private field
            (self.john, 'display_name', 'my private event', None),
            (self.george, 'display_name', 'my private event', None),
            (self.raoul, 'display_name', 'Busy', None),
            (self.portal, 'display_name', None, AccessError),
            # non-substituted private field, only owner and invitees can read,
            # other employees get an empty field
            (self.john, 'location', 'in the Sky', None),
            (self.george, 'location', 'in the Sky', None),
            (self.raoul, 'location', False, None),
            (self.portal, 'location', None, AccessError),
            # non-substituted sequence field
            (self.john, 'partner_ids', self.george.partner_id, None),
            (self.george, 'partner_ids', self.george.partner_id, None),
            (self.raoul, 'partner_ids', self.env['res.partner'], None),
            (self.portal, 'partner_ids', None, AccessError),
        ]:
            self.env.invalidate_all()
            with self.subTest("private read", user=user.display_name, field=field, error=error):
                e = event.with_user(user)
                if error:
                    with self.assertRaises(error):
                        _ = e[field]
                else:
                    self.assertEqual(e[field], expect)

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

    def test_privacy_and_show_as(self):
        """
        Simulate the "Everyone's calendar" option on the calendar dashboard.
        Check the privacy and show as combinations.
        """
        event = self.env['calendar.event'].create([
            {
                'user_id': self.john.id,
                'partner_ids': [Command.link(self.john.partner_id.id)],
                'name': 'public/busy',
                'privacy': 'public',
                'show_as': 'busy',
            },
            {
                'user_id': self.john.id,
                'partner_ids': [Command.link(self.john.partner_id.id)],
                'name': 'public/free',
                'privacy': 'public',
                'show_as': 'free',
            },
            {
                'user_id': self.john.id,
                'partner_ids': [Command.link(self.john.partner_id.id)],
                'name': 'private/busy',
                'privacy': 'private',
                'show_as': 'busy',
            },
            {
                'user_id': self.john.id,
                'partner_ids': [Command.link(self.john.partner_id.id)],
                'name': 'private/free',
                'privacy': 'private',
                'show_as': 'free',
            },
        ])

        data_john = self.env['calendar.event'].with_user(self.john).search_read([('id', 'in', event.ids)])
        john_event_name = [ev.display_name for ev in self.env['calendar.event'].browse([d['id'] for d in data_john])]
        self.assertEqual(len(data_john), 4)
        self.assertEqual(['public/busy', 'public/free (free)', 'private/busy', 'private/free (free)'], john_event_name)

        # Clear the cache otherwise some information will not be updated for the other user
        self.env.cache.clear()

        data_raoul = self.env['calendar.event'].with_user(self.raoul).search_read([('id', 'in', event.ids)])
        raoul_event_name = [ev.display_name for ev in self.env['calendar.event'].browse([d['id'] for d in data_raoul])]
        self.assertEqual(len(data_raoul), 3)
        self.assertEqual(['public/busy', 'public/free (free)', 'Busy'], raoul_event_name)

    def test_read_group_public(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['start'], groupby='start')
        self.assertTrue(data, "It should be able to read group")
        data = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['name'],
                                                                           groupby='name')
        self.assertTrue(data, "It should be able to read group")

    def test_read_group_private(self):
        event = self.create_event(self.john, privacy='private')
        result = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['name'], groupby='name')
        self.assertFalse(result, "Private events should not be fetched")


    def test_read_group_agg(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['start'], groupby='start:week')
        self.assertTrue(data, "It should be able to read group")

    def test_read_group_list(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul).read_group([('id', '=', event.id)], fields=['start'], groupby=['start'])
        self.assertTrue(data, "It should be able to read group")

    def test_private_attendee(self):
        event = self.create_event(
            self.john,
            privacy='private',
            location='in the Sky',
        )
        partners = (self.john|self.raoul).mapped('partner_id')
        event.write({'partner_ids': [(6, 0, partners.ids)]})
        self.assertEqual(self.read_event(self.raoul, event, 'location'), 'in the Sky',
                         "Owner should be able to read the event")
        with self.assertRaises(AccessError):
            self.read_event(self.portal, event, 'location')
