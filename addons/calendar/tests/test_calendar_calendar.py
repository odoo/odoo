from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestCalendarCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="cal_owner", groups="base.group_user")
        cls.other_user = new_test_user(cls.env, login="cal_other", groups="base.group_user")
        cls.user_without_access = new_test_user(cls.env, login="cal_no_access", groups="base.group_user")
        cls.calendar = cls.env["calendar.calendar"].with_user(cls.user).create({"name": "Secondary Calendar"})

    def _grant_role(self, calendar, user, role):
        return self.env["calendar.user"].sudo().create({
            "calendar_id": calendar.id,
            "user_id": user.id,
            "access_role": role,
        })

    def test_create_adds_owner_membership_via_default_get(self):
        """Creating a calendar without explicit memberships must auto-add the current user as owner."""
        # No calendar_user_id provided -> default_get should inject an owner membership for self.user.
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "My Calendar"})
        self.assertEqual(self.user, calendar.owner_id, "The creator must become the calendar owner")
        # Exactly one membership, for the creator, with role owner.
        self.assertEqual(len(calendar.calendar_user_ids), 1)
        self.assertEqual(calendar.calendar_user_ids.user_id, self.user)
        self.assertEqual(calendar.calendar_user_ids.access_role, "owner")

    def test_owner_can_write_calendar(self):
        self.calendar.with_user(self.user).write({"calendar_default_privacy": "confidential"})
        self.assertEqual(self.calendar.calendar_default_privacy, "confidential")

    def test_writer_cannot_edit_calendar_settings(self):
        """The writer role should only grant rights to edit the calendar events, not its settings."""
        self._grant_role(self.calendar, self.other_user, "writer")
        with self.assertRaises(AccessError):
            self.calendar.with_user(self.other_user).write({"calendar_default_privacy": "public"})

    def test_user_cannot_unlink_calendar_directly(self):
        self._grant_role(self.calendar, self.other_user, "owner")
        with self.assertRaises(AccessError):
            self.calendar.with_user(self.other_user).unlink()

    def test_user_can_unlink_calendar_by_removing_last_user(self):
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "Disposable"})
        self._grant_role(calendar, self.other_user, "owner")
        # The calendar still has users, so it cannot be deleted.
        calendar.with_user(self.user).calendar_user_id.unlink()
        self.assertTrue(calendar.exists())
        # Removing the last user should delete the calendar.
        calendar.with_user(self.other_user).calendar_user_id.unlink()
        self.assertFalse(calendar.exists())

    def test_color_is_stored_per_user_on_membership(self):
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "Colored"})
        calendar.with_user(self.user).color = 7
        membership = calendar.calendar_user_ids.filtered(lambda m: m.user_id == self.user)
        self.assertEqual(membership.filter_color, 7, "color must be stored on the per-user membership")
        # Reading it back through the computed field must return the same value.
        self.assertEqual(calendar.with_user(self.user).color, 7)

    def test_default_privacy_cannot_be_changed_by_non_owner(self):
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "PrivacyCal"})
        self.env["calendar.user"].create({
            "calendar_id": calendar.id,
            "user_id": self.other_user.id,
            "access_role": "writer",
        })
        with self.assertRaises(AccessError):
            calendar.with_user(self.other_user).write({"calendar_default_privacy": "public"})
        # The owner is allowed to change it.
        calendar.with_user(self.user).write({"calendar_default_privacy": "public"})
        self.assertEqual(calendar.calendar_default_privacy, "public")

    def test_primary_calendar_cannot_be_deleted(self):
        primary = self.user.primary_calendar_id
        self.assertTrue(primary, "User should have a primary calendar")
        with self.assertRaises(UserError):
            primary.with_user(self.user).unlink()

    def test_is_primary_flag(self):
        secondary = self.env["calendar.calendar"].with_user(self.user).create({"name": "Secondary"})
        self.env["calendar.user"].create({
            "calendar_id": self.other_user.primary_calendar_id.id,
            "user_id": self.user.id,
            "access_role": "writer",
        })
        self.assertTrue(self.user.primary_calendar_id.with_user(self.user).is_primary)
        self.assertFalse(secondary.with_user(self.user).is_primary)
        self.assertFalse(self.other_user.primary_calendar_id.with_user(self.user).is_primary)

    def test_portal_to_internal_user_has_calendar(self):
        user = new_test_user(self.env, login="portal_calendar_user", groups="base.group_portal")
        self.assertFalse(user.primary_calendar_id, "A portal user should not have a primary calendar.")

        # Promote portal -> internal.
        user.write({'group_ids': [
            (4, self.env.ref('base.group_user').id),
            (3, self.env.ref('base.group_portal').id),
        ]})
        self.assertTrue(user._is_internal(), "User should now be internal.")

        event = self.env['calendar.event'].create([{
            'name': 'Test event',
            'start': '2026-07-27 14:30:00',
            'stop': '2026-07-27 16:30:00',
            'user_id': user.id,
        }])

        self.assertTrue(user.primary_calendar_id, "Creating an event should create a calendar for the user.")
        self.assertEqual(user.primary_calendar_id, event.calendar_id)

        self.assertEqual(user.primary_calendar_id, user._find_or_create_primary_calendar(),
                         "_find_or_create_primary_calendar should return the user's existing primary calendar.")
