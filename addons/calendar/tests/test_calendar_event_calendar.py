from datetime import datetime

from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestCalendarEventCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="evt_user", groups="base.group_user")
        cls.secondary = cls.env["calendar.calendar"].with_user(cls.user).create({"name": "Evt Secondary"})

    def _make_event(self, **args):
        vals = {
            "name": "Event",
            "start": datetime(2026, 6, 17, 9, 0),
            "stop": datetime(2026, 6, 17, 10, 0),
            "user_id": self.user.id,
            "partner_ids": [(6, 0, self.user.partner_id.ids)],
        }
        vals.update(args)
        return self.env["calendar.event"].with_user(self.user).create(vals)

    def test_default_calendar_is_user_primary(self):
        """An event created without an explicit calendar defaults to the organizer's primary one."""
        event = self._make_event()
        self.assertEqual(event.calendar_id, self.user.primary_calendar)

    def test_event_can_be_created_in_a_secondary_calendar(self):
        """An explicit secondary calendar must be honoured at creation."""
        event = self._make_event(calendar_id=self.secondary.id)
        self.assertEqual(event.calendar_id, self.secondary)

    def test_available_calendars_match_writable_calendars(self):
        """The form domain helper exposes exactly the user's writable calendars."""
        event = self._make_event()
        self.assertEqual(
            set(event.available_calendar_ids.ids),
            set(self.user.writable_calendar_ids.ids),
        )

    def test_show_calendar_toggles(self):
        """show_calendar_in_quickcreate is on when the user has more than one writable calendar;
        show_calendar_in_form is on when the user owns the calendar."""
        event = self._make_event()
        # The default calendar is owned by the user -> form selector should appear.
        self.assertTrue(event.show_calendar_in_form)
        # While the user owns more than one calendar, the quick-create selector should appear.
        self.assertTrue(event.show_calendar_in_quickcreate)
        self.secondary.with_user(self.user).unlink()
        self.assertFalse(event.show_calendar_in_quickcreate)

    def test_effective_privacy_falls_back_to_calendar_default(self):
        """When an event has no explicit privacy, it inherits the calendar's default privacy."""
        self.secondary.with_user(self.user).write({"calendar_default_privacy": "private"})
        event = self._make_event(calendar_id=self.secondary.id, privacy=False)
        self.assertEqual(event.effective_privacy, "private")
        # An explicit privacy on the event always wins over the calendar default.
        event.write({"privacy": "public"})
        self.assertEqual(event.effective_privacy, "public")
