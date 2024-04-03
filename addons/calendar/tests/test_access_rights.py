# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError
from odoo.tools import mute_logger
from odoo import Command

class TestAccessRights(TransactionCase):

    @classmethod
    @mute_logger('odoo.tests', 'odoo.addons.auth_signup.models.res_users')
    def setUpClass(cls):
        super().setUpClass()
        cls.john = new_test_user(cls.env, login='john', groups='base.group_user')
        cls.raoul = new_test_user(cls.env, login='raoul', groups='base.group_user')
        cls.george = new_test_user(cls.env, login='george', groups='base.group_user')
        cls.portal = new_test_user(cls.env, login='pot', groups='base.group_portal')
        cls.admin_user = new_test_user(cls.env, login='admin_user', groups='base.group_partner_manager,base.group_user')

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
            event.invalidate_cache()
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
        self.assertFalse(private_location, "Private value should be obfuscated")
        self.assertEqual(public_location, 'In Hell', "Public value should not be obfuscated")

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

    def test_hide_sensitive_fields_private_events_from_uninvited_admins(self):
        """
        Ensure that it is not possible fetching sensitive fields for uninvited administrators,
        i.e. admins who are not attendees of private events. Sensitive fields are fields that
        could contain sensitive information, such as 'name', 'attendee_ids', 'location', etc.
        """
        sensitive_fields = [
            'location', 'attendee_ids', 'partner_ids', 'description', 
            'videocall_location', 'categ_ids', 'alarm_ids', 'message_ids',
        ]

        # Create event with all sensitive fields defined on it.
        event_type = self.env['calendar.event.type'].create({'name': 'type'})
        alarm = self.env['calendar.alarm'].create({'name': 'Alarm', 'alarm_type': 'email', 'interval': 'minutes', 'duration': 20})
        john_private_evt = self.create_event(
            self.john,
            name='private-event',
            privacy='private',
            location='private-location',
            description='private-description',
            attendee_status='accepted',
            partner_ids=[self.john.partner_id.id, self.raoul.partner_id.id],
            categ_ids=[event_type.id],
            alarm_ids=[alarm.id],
            videocall_location='private-url.com'
        )
        john_private_evt.message_post(body="Message to be hidden.")

        # Read the event as an uninvited administrator and ensure that the sensitive fields were hidden.
        # Do the same for the search_read method: the information of sensitive fields must be hidden. 
        private_event_domain = ('id', '=', john_private_evt.id)
        readed_event = john_private_evt.with_user(self.admin_user).read(sensitive_fields + ['name'])
        search_readed_event = self.env['calendar.event'].with_user(self.admin_user).search_read([private_event_domain])
        for event in [readed_event, search_readed_event]:
            self.assertEqual(len(event), 1, "The event itself must be fetched since the record is not hidden from uninvited admins.")
            self.assertEqual(event[0]['name'], "Busy", "Event name must be 'Busy', hiding the information from uninvited administrators.")
            for field in sensitive_fields:
                self.assertFalse(event[0][field], "Field %s contains private information, it must be hidden from uninvited administrators." % field)

        # Ensure that methods like 'mapped', 'filtered', 'filtered_domain', '_search' and 'read_group' do not
        # bypass the override of read, which will hide the private information of the events from uninvited administrators.
        sensitive_stored_fields = ['name', 'location', 'description', 'videocall_location']
        searched_event = self.env['calendar.event'].with_user(self.admin_user).search([private_event_domain])

        for field in sensitive_stored_fields:
            # For each method, fetch the information of the private event as an uninvited administrator.
            check_mapped_event = searched_event.with_user(self.admin_user).mapped(field)
            check_filtered_event = searched_event.with_user(self.admin_user).filtered(lambda ev: ev.id == john_private_evt.id)
            check_filtered_domain = searched_event.with_user(self.admin_user).filtered_domain([private_event_domain])
            check_search_query = self.env['calendar.event'].with_user(self.admin_user)._search([private_event_domain])
            check_search_object = self.env['calendar.event'].with_user(self.admin_user).browse(check_search_query)
            check_read_group = self.env['calendar.event'].with_user(self.admin_user).read_group([private_event_domain], [field], [field])

            if field == 'name':
                # The 'name' field is manually changed to 'Busy' by default. We need to ensure it is shown as 'Busy' in all following methods.
                self.assertEqual(check_mapped_event, ['Busy'], 'Private event name should be shown as Busy using the mapped function.')
                self.assertEqual(check_filtered_event.name, 'Busy', 'Private event name should be shown as Busy using the filtered function.')
                self.assertEqual(check_filtered_domain.name, 'Busy', 'Private event name should be shown as Busy using the filtered_domain function.')
                self.assertEqual(check_search_object.name, 'Busy', 'Private event name should be shown as Busy using the _search function.')
            else:
                # The remaining private fields should be falsy for uninvited administrators.
                self.assertFalse(check_mapped_event[0], 'Private event field "%s" should be hidden when using the mapped function.' % field)
                self.assertFalse(check_filtered_event[field], 'Private event field "%s" should be hidden when using the filtered function.' % field)
                self.assertFalse(check_filtered_domain[field], 'Private event field "%s" should be hidden when using the filtered_domain function.' % field)
                self.assertFalse(check_search_object[field], 'Private event field "%s" should be hidden when using the _search function.' % field)

            # Private events are excluded from read_group by default, ensure that we do not fetch it.
            self.assertFalse(len(check_read_group), 'Private event should be hidden using the function _read_group.')
