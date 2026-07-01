from psycopg2 import IntegrityError

from odoo.addons.calendar.tests.test_calendar_calendar import TestCalendarCalendar
from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestCalendarCalendarUser(TestCalendarCalendar):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_membership = cls.calendar.calendar_users.filtered(lambda m: m.user_id == cls.user)

    def test_unique_membership_per_user_and_calendar(self):
        # The owner membership already exists from create(); a duplicate must violate the index.
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["calendar.calendar.user"].create({
                    "calendar_id": self.calendar.id,
                    "user_id": self.user.id,
                    "access_role": "reader",
                })
                self.env.cr.flush()

    def test_single_primary_calendar_per_user(self):
        # The user already owns a primary calendar (from the res.users create override).
        second_calendar = self.env["calendar.calendar"].with_user(self.user).create({"name": "Another"})
        with self.assertRaises(AccessError):
            with self.env.cr.savepoint():
                # Promote a second membership to primary for the same user -> must be rejected.
                second_calendar.calendar_users.filtered(
                    lambda m: m.user_id == self.user
                ).write({"is_primary": True})
                self.env.cr.flush()

    def test_non_superuser_cannot_edit_protected_fields(self):
        membership = self.calendar.calendar_users.filtered(lambda m: m.user_id == self.user)
        with self.assertRaises(AccessError):
            membership.with_user(self.user).write({"access_role": "reader"})

    def test_non_superuser_can_edit_filter_fields(self):
        """Filter-only fields (color, active, checked) remain editable by a regular user."""
        membership = self.calendar.calendar_users.filtered(lambda m: m.user_id == self.user)
        membership.with_user(self.user).write({
            "filter_color": 4,
            "is_filter_active": False,
            "is_filter_checked": False,
        })
        self.assertEqual(membership.filter_color, 4)
        self.assertFalse(membership.is_filter_active)
        self.assertFalse(membership.is_filter_checked)

    def test_owner_can_invite_other_user(self):
        membership = self.env["calendar.calendar.user"].with_user(self.user).create({
            "calendar_id": self.calendar.id,
            "user_id": self.other_user.id,
            "access_role": "reader",
        })
        self.assertEqual(membership.user_id, self.other_user)

    def test_non_owner_cannot_grant_self_access(self):
        with self.assertRaises(AccessError):
            self.env["calendar.calendar.user"].with_user(self.other_user).create({
                "calendar_id": self.calendar.id,
                "user_id": self.other_user.id,
                "access_role": "writer",
            })

    def test_non_owner_cannot_grant_access_to_third_party(self):
        with self.assertRaises(AccessError):
            self.env["calendar.calendar.user"].with_user(self.other_user).create({
                "calendar_id": self.calendar.id,
                "user_id": self.user_without_access.id,
                "access_role": "reader",
            })

    def test_writer_cannot_grant_access(self):
        self._grant_role(self.calendar, self.other_user, "writer")
        with self.assertRaises(AccessError):
            self.env["calendar.calendar.user"].with_user(self.other_user).create({
                "calendar_id": self.calendar.id,
                "user_id": self.user_without_access.id,
                "access_role": "reader",
            })

    def test_non_owner_cannot_write_others_membership(self):
        self._grant_role(self.calendar, self.other_user, "reader")
        with self.assertRaises(AccessError):
            self.user_membership.with_user(self.other_user).write({"filter_color": 9})

    def test_member_can_unlink_own_membership(self):
        self._grant_role(self.calendar, self.other_user, "reader")
        membership = self.calendar.calendar_users.filtered(lambda m: m.user_id == self.other_user)
        membership.with_user(self.other_user).unlink()
        self.assertFalse(membership.exists())

    def test_non_owner_cannot_unlink_others_membership(self):
        self._grant_role(self.calendar, self.other_user, "writer")
        with self.assertRaises(AccessError):
            self.user_membership.with_user(self.other_user).unlink()

    def test_owner_can_unlink_others_membership(self):
        self._grant_role(self.calendar, self.other_user, "reader")
        membership = self.calendar.calendar_users.filtered(lambda m: m.user_id == self.other_user)
        membership.with_user(self.user).unlink()
        self.assertFalse(membership.exists())
