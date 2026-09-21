from datetime import datetime, timedelta

from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


class CalendarPrivacyCommon:
    """Three employees: the organizer, an invitee, and an uninvited bystander.

    A plain mixin, not a base test case: only the route tests need an HTTP
    server, and making everything an `HttpCase` meant every one of these was
    silently skipped in any lane running `--no-http`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("calendar.block_mail", True)
        cls.organizer = new_test_user(
            cls.env, "privacy_organizer", groups="base.group_user"
        )
        cls.invitee = new_test_user(
            cls.env, "privacy_invitee", groups="base.group_user"
        )
        cls.bystander = new_test_user(
            cls.env, "privacy_bystander", groups="base.group_user"
        )
        cls.start = datetime(2035, 3, 15, 10, 0)

    def _make_event(self, privacy, **kwargs):
        return (
            self.env["calendar.event"]
            .with_user(self.organizer)
            .create(
                {
                    "name": "SECRET therapy",
                    "location": "SECRET clinic",
                    "privacy": privacy,
                    "start": self.start,
                    "stop": self.start + timedelta(hours=1),
                    "partner_ids": [
                        (
                            6,
                            0,
                            [self.organizer.partner_id.id, self.invitee.partner_id.id],
                        )
                    ],
                    **kwargs,
                }
            )
        )


@tagged("post_install", "-at_install")
class TestAttendeePrivacy(CalendarPrivacyCommon, TransactionCase):
    """`calendar.attendee` used to expose every private event's participants."""

    def test_attendees_of_a_private_event_are_not_searchable(self):
        event = self._make_event("private")
        self.env.flush_all()
        Attendee = self.env["calendar.attendee"]
        self.assertFalse(
            Attendee.with_user(self.bystander).search([("event_id", "=", event.id)]),
            "an uninvited employee must not find the attendees of a private event",
        )
        self.assertEqual(
            len(Attendee.with_user(self.invitee).search([("event_id", "=", event.id)])),
            2,
            "an invitee still sees who else is coming",
        )

    def test_attendees_of_a_private_event_are_not_readable_by_id(self):
        event = self._make_event("private")
        self.env.flush_all()
        attendee_ids = event.sudo().attendee_ids.ids
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.env["calendar.attendee"].with_user(self.bystander).browse(
                attendee_ids
            ).read(["partner_id", "state"])

    def test_attendees_of_a_private_event_do_not_leak_through_read_group(self):
        event = self._make_event("private")
        self.env.flush_all()
        self.assertFalse(
            self.env["calendar.attendee"]
            .with_user(self.bystander)
            ._read_group([("event_id", "=", event.id)], ["state"], ["__count"]),
            "grouping is an oracle too",
        )

    def test_public_event_attendees_stay_visible(self):
        event = self._make_event("public")
        self.env.flush_all()
        self.assertEqual(
            len(
                self.env["calendar.attendee"]
                .with_user(self.bystander)
                .search([("event_id", "=", event.id)])
            ),
            2,
            "a public event's attendees are not secret",
        )

    def test_access_token_is_never_readable_by_a_plain_employee(self):
        """The token is the credential of the `calendar` auth method."""
        event = self._make_event("public")
        self.env.flush_all()
        attendee_ids = event.sudo().attendee_ids.ids
        for user, label in (
            (self.bystander, "a bystander"),
            (self.invitee, "an invitee"),
            (self.organizer, "the organizer"),
        ):
            self.env.invalidate_all()
            with self.assertRaises(
                AccessError, msg=f"{label} must not read invitation tokens"
            ):
                self.env["calendar.attendee"].with_user(user).browse(attendee_ids).read(
                    ["access_token"]
                )
        self.env.invalidate_all()
        self.assertTrue(
            all(
                self.env["calendar.attendee"]
                .sudo()
                .browse(attendee_ids)
                .mapped("access_token")
            ),
            "the mail templates render through sudo() and must still see the tokens",
        )


@tagged("post_install", "-at_install")
class TestRecurrencePrivacy(CalendarPrivacyCommon, TransactionCase):
    """`calendar.recurrence` used to be readable and writable by anyone."""

    def _make_recurrence(self, privacy):
        return self._make_event(
            privacy,
            recurrency=True,
            repeat_unit="week",
            thu=True,
            repeat_type="count",
            repeat_number=3,
            event_tz="UTC",
        )

    def test_private_recurrence_is_not_readable(self):
        event = self._make_recurrence("private")
        self.env.flush_all()
        recurrence_id = event.sudo().recurrence_id.id
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.env["calendar.recurrence"].with_user(self.bystander).browse(
                recurrence_id
            ).read(["name", "rrule"])

    def test_private_recurrence_is_not_writable(self):
        event = self._make_recurrence("private")
        self.env.flush_all()
        recurrence_id = event.sudo().recurrence_id.id
        with self.assertRaises(AccessError):
            self.env["calendar.recurrence"].with_user(self.bystander).browse(
                recurrence_id
            ).write({"repeat_number": 99})

    def test_owner_still_drives_their_own_recurrence(self):
        event = self._make_recurrence("private")
        self.env.flush_all()
        self.assertEqual(len(event.recurrence_id.calendar_event_ids), 3)
        event.recurrence_id.with_user(self.organizer).write({"repeat_number": 4})
        self.env.flush_all()
        self.assertEqual(event.recurrence_id.repeat_number, 4)


@tagged("post_install", "-at_install")
class TestCalendarFiltersPrivacy(CalendarPrivacyCommon, TransactionCase):
    """`calendar.filters` had no record rule and a public unlink-everything RPC."""

    def test_filters_are_private_to_their_user(self):
        own = (
            self.env["calendar.filters"]
            .with_user(self.organizer)
            .create(
                {
                    "user_id": self.organizer.id,
                    "partner_id": self.invitee.partner_id.id,
                }
            )
        )
        self.env.flush_all()
        self.assertFalse(
            self.env["calendar.filters"]
            .with_user(self.bystander)
            .search([("user_id", "=", self.organizer.id)]),
            "one employee must not see another's calendar overlays",
        )
        with self.assertRaises(AccessError):
            self.env["calendar.filters"].with_user(self.bystander).browse(
                own.id
            ).unlink()
        self.assertTrue(own.exists())

    def test_the_unlink_everything_rpc_is_gone(self):
        self.assertFalse(
            hasattr(self.env["calendar.filters"], "unlink_from_partner_id"),
            "unlink_from_partner_id was an RPC-callable cross-user delete with no caller",
        )


@tagged("post_install", "-at_install")
class TestInvitationTokenRoutes(CalendarPrivacyCommon, HttpCase):
    """An empty token is not a token."""

    def test_empty_token_does_not_authenticate(self):
        event = self._make_event("public")
        self.env.flush_all()
        # An attendee whose token is NULL: not something the ORM produces, but
        # the routes must not treat "no token" as "match the tokenless rows".
        self.env.cr.execute(
            "UPDATE calendar_attendee SET access_token = NULL WHERE event_id = %s",
            (event.id,),
        )
        self.env.invalidate_all()
        for route in (
            "/calendar/meeting/view",
            "/calendar/meeting/accept",
            "/calendar/meeting/decline",
        ):
            response = self.url_open(f"{route}?token=&id={event.id}")
            self.assertEqual(
                response.status_code,
                404,
                f"{route} must reject an empty token, not match a NULL one",
            )
        self.env.invalidate_all()
        self.assertEqual(
            set(event.sudo().attendee_ids.mapped("state")),
            {"accepted", "needsAction"},
            "no state was changed by the rejected requests",
        )

    def test_empty_token_on_the_event_routes(self):
        """Events legitimately have a NULL token whenever they have no videocall."""
        event = self._make_event("public")
        self.env.flush_all()
        self.assertFalse(event.sudo().access_token)
        self.authenticate("privacy_bystander", "privacy_bystander")
        response = self.url_open("/calendar/meeting/join?token=")
        self.assertEqual(
            response.status_code,
            404,
            "an empty token must not match every tokenless event",
        )
        self.env.invalidate_all()
        self.assertNotIn(self.bystander.partner_id, event.sudo().partner_ids)


@tagged("post_install", "-at_install")
class TestPrivacyDomainFallback(CalendarPrivacyCommon, TransactionCase):
    """The domain and the predicate must agree about a user with no settings row."""

    def test_owner_without_settings_row_is_not_treated_as_private(self):
        # `_check_private_event_conditions` falls back to the config parameter
        # for such an owner; `_get_domain_default_privacy` used not to, so the
        # event was public to the predicate and invisible to every search.
        owner = new_test_user(self.env, "no_settings_owner", groups="base.group_user")
        owner.sudo().res_users_settings_id.unlink()
        self.env.invalidate_all()
        event = (
            self.env["calendar.event"]
            .with_user(owner)
            .create(
                {
                    "name": "plain event",
                    "start": self.start,
                    "stop": self.start + timedelta(hours=1),
                    "partner_ids": [(6, 0, [owner.partner_id.id])],
                }
            )
        )
        self.env.flush_all()
        self.assertFalse(event.privacy)
        self.assertFalse(
            event._check_private_event_conditions.__func__(
                event.with_user(self.bystander)
            )
        )
        self.assertIn(
            event,
            self.env["calendar.event"]
            .with_user(self.bystander)
            .search([("name", "=", "plain event")]),
            "the search domain must reach the same verdict as the predicate",
        )


@tagged("post_install", "-at_install")
class TestRecurrenceCountCap(CalendarPrivacyCommon, TransactionCase):
    def test_a_count_beyond_the_cap_is_refused_not_silently_truncated(self):
        with self.assertRaises(UserError):
            self.env["calendar.event"].with_user(self.organizer).create(
                {
                    "name": "too many",
                    "start": self.start,
                    "stop": self.start + timedelta(hours=1),
                    "recurrency": True,
                    "repeat_unit": "day",
                    "repeat_type": "count",
                    "repeat_number": 800,
                    "event_tz": "UTC",
                }
            )
