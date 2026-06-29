from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestResUsersCalendars(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="ru_user", groups="base.group_user")
        cls.other = new_test_user(cls.env, login="ru_other", groups="base.group_user")

    def test_new_user_has_one_owned_primary_calendar(self):
        """Each new user should own one primary calendar."""
        self.assertTrue(self.user.primary_calendar)
        self.assertIn(self.user, self.user.primary_calendar.owners)
        primary_memberships = self.user.calendar_users.filtered(
            lambda m: m.is_primary and m.access_role == "owner"
        )
        self.assertEqual(len(primary_memberships), 1)

    def test_calendar_ids_includes_primary_and_secondary(self):
        """calendar_ids must list every calendar the user is a member of."""
        secondary = self.env["calendar.calendar"].with_user(self.user).create({"name": "Sec"})
        self.assertIn(self.user.primary_calendar, self.user.calendar_ids)
        self.assertIn(secondary, self.user.calendar_ids)

    def test_writable_calendar_ids_excludes_read_only_shares(self):
        """writable_calendar_ids must contain owner/writer calendars only."""
        # A calendar shared with the user as read-only must NOT be writable.
        foreign = self.env["calendar.calendar"].with_user(self.other).create({"name": "Foreign"})
        self.env["calendar.calendar.user"].create({
            "calendar_id": foreign.id,
            "user_id": self.user.id,
            "access_role": "reader",
        })
        self.assertIn(self.user.primary_calendar, self.user.writable_calendar_ids)
        self.assertNotIn(foreign, self.user.writable_calendar_ids)

    def test_get_secondary_calendars(self):
        """get_secondary_calendars returns every readable calendar except the user's own primary."""
        secondary = self.env["calendar.calendar"].with_user(self.user).create({"name": "Sec2"})
        foreign = self.env["calendar.calendar"].with_user(self.other).create({"name": "Foreign"})
        self.env["calendar.calendar.user"].create({
            "calendar_id": foreign.id,
            "user_id": self.user.id,
            "access_role": "reader",
        })
        secondaries = self.user.get_secondary_calendars()
        self.assertIn(secondary, secondaries)
        self.assertIn(foreign, secondaries)
        self.assertNotIn(self.user.primary_calendar, secondaries)
