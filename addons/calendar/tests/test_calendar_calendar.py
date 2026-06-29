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
        return self.env["calendar.calendar.user"].sudo().create({
            "calendar_id": calendar.id,
            "user_id": user.id,
            "access_role": role,
        })

    def test_create_adds_owner_membership_via_default_get(self):
        """Creating a calendar without explicit memberships must auto-add the current user as owner."""
        # No calendar_users provided -> default_get should inject an owner membership for self.user.
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "My Calendar"})
        self.assertIn(self.user, calendar.owners, "The creator must become the calendar owner")
        # Exactly one membership, for the creator, with role owner.
        self.assertEqual(len(calendar.calendar_users), 1)
        self.assertEqual(calendar.calendar_users.user_id, self.user)
        self.assertEqual(calendar.calendar_users.access_role, "owner")

    def test_access_role_and_access_flags(self):
        owner_view = self.calendar.with_user(self.user)
        self.assertEqual(owner_view.user_access_role, "owner")
        self.assertTrue(owner_view.user_has_read_access)
        self.assertTrue(owner_view.user_has_write_access)

        self.env["calendar.calendar.user"].with_user(self.user).create({
            "calendar_id": self.calendar.id,
            "user_id": self.other_user.id,
            "access_role": "reader",
        })
        reader_view = self.calendar.with_user(self.other_user)
        self.assertEqual(reader_view.user_access_role, "reader")
        self.assertTrue(reader_view.user_has_read_access)
        self.assertFalse(reader_view.user_has_write_access)

        no_access_view = self.calendar.with_user(self.user_without_access)
        self.assertEqual(no_access_view.user_access_role, 'none')
        self.assertFalse(no_access_view.user_has_read_access)
        self.assertFalse(no_access_view.user_has_write_access)

    def test_owner_can_write_calendar(self):
        self.calendar.with_user(self.user).write({"name": "Renamed by owner"})
        self.assertEqual(self.calendar.name, "Renamed by owner")

    def test_writer_can_write_calendar(self):
        self._grant_role(self.calendar, self.other_user, "writer")
        self.calendar.with_user(self.other_user).write({"name": "Renamed by writer"})
        self.assertEqual(self.calendar.name, "Renamed by writer")

    def test_reader_cannot_write_calendar(self):
        self._grant_role(self.calendar, self.other_user, "reader")
        self.assertFalse(self.calendar.with_user(self.other_user).user_has_write_access)
        with self.assertRaises(AccessError):
            self.calendar.with_user(self.other_user).write({"name": "Should fail"})

    def test_writer_cannot_unlink_calendar(self):
        self._grant_role(self.calendar, self.other_user, "writer")
        with self.assertRaises(AccessError):
            self.calendar.with_user(self.other_user).unlink()

    def test_owner_can_unlink_calendar(self):
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "Disposable"})
        calendar.with_user(self.user).unlink()
        self.assertFalse(calendar.exists())

    def test_search_user_has_read_and_write_access(self):
        """The search methods for the access flags must return the right calendars per user."""
        owned = self.env["calendar.calendar"].with_user(self.user).create({"name": "Owned"})
        shared_ro = self.env["calendar.calendar"].with_user(self.other_user).create({"name": "Foreign"})
        self.env["calendar.calendar.user"].create({
            "calendar_id": shared_ro.id,
            "user_id": self.user.id,
            "access_role": "reader",
        })

        readable = self.env["calendar.calendar"].with_user(self.user).search(
            [("user_has_read_access", "=", True)]
        )
        self.assertIn(owned, readable)
        self.assertIn(shared_ro, readable)

        writable = self.env["calendar.calendar"].with_user(self.user).search(
            [("user_has_write_access", "=", True)]
        )
        self.assertIn(owned, writable)
        self.assertNotIn(shared_ro, writable)

    def test_color_is_stored_per_user_on_membership(self):
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "Colored"})
        calendar.with_user(self.user).color = 7
        membership = calendar.calendar_users.filtered(lambda m: m.user_id == self.user)
        self.assertEqual(membership.filter_color, 7, "color must be stored on the per-user membership")
        # Reading it back through the computed field must return the same value.
        self.assertEqual(calendar.with_user(self.user).color, 7)

    def test_default_privacy_cannot_be_changed_by_non_owner(self):
        calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "PrivacyCal"})
        self.env["calendar.calendar.user"].create({
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
        primary = self.user.primary_calendar
        self.assertTrue(primary, "User should have a primary calendar")
        with self.assertRaises(UserError):
            primary.with_user(self.user).unlink()

    def test_is_primary_flag(self):
        secondary = self.env["calendar.calendar"].with_user(self.user).create({"name": "Secondary"})
        self.env["calendar.calendar.user"].create({
            "calendar_id": self.other_user.primary_calendar.id,
            "user_id": self.user.id,
            "access_role": "writer",
        })
        self.assertTrue(self.user.primary_calendar.with_user(self.user).is_primary)
        self.assertFalse(secondary.with_user(self.user).is_primary)
        self.assertFalse(self.other_user.primary_calendar.with_user(self.user).is_primary)
