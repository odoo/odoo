# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, new_test_user
from odoo.tests import Form
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
        cls.admin_system_user = new_test_user(cls.env, login='admin_system_user', groups='base.group_system')

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
        data = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', event.id)], groupby=['start:month'])
        self.assertTrue(data, "It should be able to read group")
        data = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', event.id)], groupby=['name'])
        self.assertTrue(data, "It should be able to read group")

    def test_read_group_private(self):
        event = self.create_event(self.john, privacy='private')
        result = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', event.id)], groupby=['name'])
        self.assertFalse(result, "Private events should not be fetched")

    def test_read_group_agg(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', event.id)], groupby=['start:week'])
        self.assertTrue(data, "It should be able to read group")

    def test_read_group_list(self):
        event = self.create_event(self.john)
        data = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', event.id)], groupby=['start:month'])
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

    def test_event_default_privacy_as_private(self):
        """ Check the privacy of events with owner's event default privacy as 'private'. """
        # Set organizer default privacy as 'private' and create event privacies default, public, private and confidential.
        self.george.with_user(self.george).calendar_default_privacy = 'private'
        default_event = self.create_event(self.george)
        public_event = self.create_event(self.george, privacy='public')
        private_event = self.create_event(self.george, privacy='private')
        confidential_event = self.create_event(self.george, privacy='confidential')

        # With another user who is not an event attendee, try accessing the events.
        query_default_event = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', default_event.id)], groupby=['name'])
        query_public_event = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', public_event.id)], groupby=['name'])
        query_private_event = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', private_event.id)], groupby=['name'])
        query_confidential_event = self.env['calendar.event'].with_user(self.raoul)._read_group([('id', '=', confidential_event.id)], groupby=['name'])

        # Ensure that each event is accessible or not according to its privacy.
        self.assertFalse(query_default_event, "Event must be inaccessible because the user has default privacy as 'private'.")
        self.assertTrue(query_public_event, "Public event must be accessible to other users.")
        self.assertFalse(query_private_event, "Private event must be inaccessible to other users.")
        self.assertTrue(query_confidential_event, "Confidential event must be accessible to other internal users.")

    def test_edit_private_event_of_other_user(self):
        """
        Ensure that it is not possible editing the private event of another user when the current user is not an
        attendee/organizer of that event. Attendees should be able to edit it, others will receive AccessError on write.
        """
        def ensure_user_can_update_event(self, event, user):
            event.with_user(user).write({'name': user.name})
            self.assertEqual(event.name, user.name, 'Event name should be updated by user %s' % user.name)

        # Prepare events attendees/partners including organizer (john) and another user (raoul).
        events_attendees = [
            (0, 0, {'partner_id': self.john.partner_id.id, 'state': 'accepted'}),
            (0, 0, {'partner_id': self.raoul.partner_id.id, 'state': 'accepted'})
        ]
        events_partners = [self.john.partner_id.id, self.raoul.partner_id.id]

        # Set calendar default privacy as private and create a normal event, only attendees/organizer can edit it.
        self.john.with_user(self.john).calendar_default_privacy = 'private'
        johns_default_privacy_event = self.create_event(self.john, name='my event with default privacy', attendee_ids=events_attendees, partner_ids=events_partners)
        ensure_user_can_update_event(self, johns_default_privacy_event, self.john)
        ensure_user_can_update_event(self, johns_default_privacy_event, self.raoul)
        with self.assertRaises(AccessError):
            self.assertEqual(len(self.john.res_users_settings_id), 1, "Res Users Settings for the user is not defined.")
            self.assertEqual(self.john.res_users_settings_id.calendar_default_privacy, 'private', "Privacy field update was lost.")
            johns_default_privacy_event.with_user(self.george).write({'name': 'blocked-update-by-non-attendee'})

        # Set calendar default privacy as public and create a private event, only attendees/organizer can edit it.
        self.john.with_user(self.john).calendar_default_privacy = 'public'
        johns_private_event = self.create_event(self.john, name='my private event', privacy='private', attendee_ids=events_attendees, partner_ids=events_partners)
        ensure_user_can_update_event(self, johns_private_event, self.john)
        ensure_user_can_update_event(self, johns_private_event, self.raoul)
        with self.assertRaises(AccessError):
            self.assertEqual(len(self.john.res_users_settings_id), 1, "Res Users Settings for the user is not defined.")
            self.assertEqual(self.john.res_users_settings_id.calendar_default_privacy, 'public', "Privacy field update was lost.")
            johns_private_event.with_user(self.george).write({'name': 'blocked-update-by-non-attendee'})

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

    def test_admin_cant_edit_uninvited_private_events(self):
        """
        Administrators must not be able to edit private events that they are not attending.
        The event is property of the organizer and its attendees only (for private events in the backend).
        """
        john_private_evt = self.create_event(self.john, name='priv', privacy='private', location='loc_1', description='priv')

        # Ensure that uninvited admin can not edit the event since it is not an event partner (attendee).
        with self.assertRaises(AccessError):
            john_private_evt.with_user(self.admin_user)._compute_user_can_edit()

        # Ensure that AccessError is raised when trying to update the uninvited event.
        with self.assertRaises(AccessError):
            john_private_evt.with_user(self.admin_user).write({'name': 'forbidden-update'})

    def test_admin_edit_uninvited_non_private_events(self):
        """
        Administrators must be able to edit (public, confidential) events that they are not attending.
        This feature is widely used for customers since it is useful editing normal user's events on their behalf.
        """
        for privacy in ['public', 'confidential']:
            john_event = self.create_event(self.john, name='event', privacy=privacy, location='loc')

            # Ensure that uninvited admin can edit this type of event.
            john_event.with_user(self.admin_user)._compute_user_can_edit()
            self.assertTrue(john_event.user_can_edit, f"Event of type {privacy} must be editable by uninvited admins.")
            john_event.with_user(self.admin_user).write({'name': 'update'})
            self.assertEqual(john_event.name, 'update', f"Simple write must be allowed for uninvited admins in {privacy} events.")

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

    def test_user_update_calendar_default_privacy(self):
        """
        Ensure that administrators and normal users can update their own calendar
        default privacy from the 'res.users' related field without throwing any error.
        Updates from others users are blocked during write (except for Default User Template from admins).
        """
        for privacy in ['public', 'private', 'confidential']:
            # Update normal user and administrator 'calendar_default_privacy' simulating their own update.
            self.john.with_user(self.john).write({'calendar_default_privacy': privacy})
            self.admin_system_user.with_user(self.admin_system_user).write({'calendar_default_privacy': privacy})
            self.assertEqual(self.john.calendar_default_privacy, privacy, 'Normal user must be able to update its calendar default privacy.')
            self.assertEqual(self.admin_system_user.calendar_default_privacy, privacy, 'Admin must be able to update its calendar default privacy.')

            # Update the Default 'calendar.default_privacy' as an administrator.
            self.env['ir.config_parameter'].sudo().set_param("calendar.default_privacy", privacy)

            # All calendar default privacy updates must be blocked during write.
            with self.assertRaises(AccessError):
                self.john.with_user(self.admin_system_user).write({'calendar_default_privacy': privacy})
            with self.assertRaises(AccessError):
                self.admin_system_user.with_user(self.john).write({'calendar_default_privacy': privacy})

    def test_check_private_event_conditions_by_internal_user(self):
        """ Ensure that internal user (non-admin) will see that admin's event is private. """
        # Update admin calendar_default_privacy with 'private' option. Create private event for admin.
        self.admin_user.with_user(self.admin_user).write({'calendar_default_privacy': 'private'})
        admin_user_private_evt = self.create_event(self.admin_user, name='My Event', privacy=False, partner_ids=[self.admin_user.partner_id.id])

        # Ensure that intrnal user will see the admin's event as private.
        self.assertTrue(
            admin_user_private_evt.with_user(self.raoul)._check_private_event_conditions(),
            "Privacy check must be True since the new event is private (following John's calendar default privacy)."
        )

    def test_recurring_event_with_alarms_for_non_admin(self):
        """
        Test that non-admin user can modify recurring events with alarms
        without triggering access errors when accessing ir.cron.trigger records.
        """

        alarm = self.env['calendar.alarm'].create({
            'name': '15 minutes before',
            'alarm_type': 'email',
            'duration': 15,
            'interval': 'minutes',
        })

        with Form(self.env['calendar.event'].with_user(self.john)) as event_form:
            event_form.name = 'yearly Team Meeting'
            event_form.start = datetime(2024, 1, 15, 9, 0)
            event_form.stop = datetime(2024, 1, 15, 10, 0)
            event_form.recurrency = True
            event_form.rrule_type_ui = 'yearly'
            event_form.count = 3
            event_form.alarm_ids.add(alarm)
            event_form.partner_ids.add(self.john.partner_id)
            recurring_event = event_form.save()

        self.assertTrue(recurring_event.recurrence_id, "Recurrence should be created")

        with Form(recurring_event.with_user(self.john)) as form:
            form.partner_ids.add(self.raoul.partner_id)

        self.assertIn(self.raoul.partner_id.id, recurring_event.partner_ids.ids, "Partner should be added as attendee")
