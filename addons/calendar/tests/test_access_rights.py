# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

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
        # invalidate cache before reading, otherwise read() might leak private data
        self.env.invalidate_all()
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

    def test_meeting_edit_access_notification_handle_in_odoo(self):
        # set notifications to "handle in Odoo" in Preferences for john, raoul, and george
        (self.john | self.raoul | self.george).write({'notification_type': 'inbox'})

        # raoul creates a meeting for john, excluding themselves
        meeting = self.env['calendar.event'].with_user(self.raoul).create({
            'name': 'Test Meeting',
            'start': datetime.now(),
            'stop': datetime.now() + timedelta(hours=2),
            'user_id': self.john.id,
            'partner_ids': [(4, self.raoul.partner_id.id)],
        })

        # george tries to modify the start date of the meeting to a future date
        # this verifies that users with "handle in Odoo" notification setting can
        # successfully edit meetings created by other users. If this write fails,
        # it indicates that there might be an issue with access rights for meeting attendees.
        meeting = meeting.with_user(self.george)
        meeting.write({
            'start': datetime.now() + timedelta(days=2),
            'stop': datetime.now() + timedelta(days=2, hours=2),
        })

    def test_admin_cant_fetch_uninvited_private_events(self):
        """
        Administrators must not be able to fetch information from private events which
        they are not attending (i.e. events which it is not an event partner). The privacy
        of the event information must always be kept. Public events can be read normally.
        """
        john_private_evt = self.create_event(self.john, name='priv', privacy='private', location='loc_1', description='priv')
        john_public_evt = self.create_event(self.john, name='pub', privacy='public', location='loc_2', description='pub')
        self.env.invalidate_all()

        # For the private event, ensure that no private field can be read, such as: 'name', 'location' and 'description'.
        for (field, value) in [('name', 'Busy'), ('location', False), ('description', False)]:
            hidden_information = self.read_event(self.admin_user, john_private_evt, field)
            self.assertEqual(hidden_information, value, "The field '%s' information must be hidden, even for uninvited admins." % field)

        # For the public event, ensure that the same fields can be read by the admin.
        for (field, value) in [('name', 'pub'), ('location', 'loc_2'), ('description', "<p>pub</p>")]:
            field_information = self.read_event(self.admin_user, john_public_evt, field)
            self.assertEqual(str(field_information), value, "The field '%s' information must be readable by the admin." % field)

    def test_admin_cant_edit_uninvited_events(self):
        """
        Administrators must not be able to edit events that they are not attending.
        The event is property of the organizer and its attendees only (for private events in the backend).
        """
        john_private_evt = self.create_event(self.john, name='priv', privacy='private', location='loc_1', description='priv')

        # Ensure that uninvited admin can not edit the event since it is not an event partner (attendee).
        with self.assertRaises(AccessError):
            john_private_evt.with_user(self.admin_user)._compute_user_can_edit()

        # Ensure that AccessError is raised when trying to update the uninvited event.
        with self.assertRaises(AccessError):
            john_private_evt.with_user(self.admin_user).write({'name': 'forbidden-update'})

    def test_hide_sensitive_fields_private_events_from_uninvited_admins(self):
        """
        Ensure that it is not possible fetching sensitive fields for uninvited administrators,
        i.e. admins who are not attendees of private events. Sensitive fields are fields that
        could contain sensitive information, such as 'name', 'description', 'location', etc.
        """
        sensitive_fields = {
            'name', 'location', 'attendee_ids', 'description', 'alarm_ids',
            'categ_ids', 'message_ids', 'partner_ids', 'videocall_location'
        }

        # Create event with all sensitive fields defined on it.
        john_private_evt = self.create_event(
            self.john,
            name='private-event',
            privacy='private',
            location='private-location',
            description='private-description',
            partner_ids=[self.john.partner_id.id, self.raoul.partner_id.id],
            videocall_location='private-url.com'
        )
        john_private_evt.message_post(body="Message to be hidden.")

        # Search_fetch the event as an uninvited administrator and ensure that the sensitive fields were hidden.
        # This method goes through the _fetch_query method which covers all variations of read(), search_read() and export_data().
        private_event_domain = ('id', '=', john_private_evt.id)
        search_fetch_event = self.env['calendar.event'].with_user(self.admin_user).search_fetch([private_event_domain], sensitive_fields)
        self.assertEqual(len(search_fetch_event), 1, "The event itself must be fetched since the record is not hidden from uninvited admins.")
        for field in sensitive_fields:
            if field == 'name':
                self.assertEqual(search_fetch_event['name'], "Busy", "Event name must be 'Busy', hiding the information from uninvited administrators.")
            else:
                self.assertFalse(search_fetch_event[field], "Field %s contains private information, it must be hidden from uninvited administrators." % field)
