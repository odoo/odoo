# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mail.tools.discuss import Store
from odoo.tests import HttpCase, new_test_user
from ..models.mail_presence import PRESENCE_OUTDATED_TIMER
from odoo.addons.bus.tests.common import BusCase, BusResult


class TestMailPresence(BusCase, HttpCase):
    def test_bus_presence_auto_vacuum(self):
        user = new_test_user(self.env, login="bob_user")
        more_than_away_timer_ago = datetime.now() - timedelta(seconds=PRESENCE_OUTDATED_TIMER + 1)
        more_than_away_timer_ago = more_than_away_timer_ago.replace(microsecond=0)
        with self.mock_datetime_and_now(more_than_away_timer_ago):
            self.env["mail.presence"]._update_presence(user)
        self.assertEqual(user.presence_ids.last_poll, more_than_away_timer_ago)
        self.env["mail.presence"]._gc_bus_presence()
        self.assertEqual(user.presence_ids.status, "offline")
        self.assertEqual(user.presence_ids.last_poll, more_than_away_timer_ago)
        self.assertEqual(user.im_status, "offline")

    def test_bus_presence_auto_vacuum_version_never_goes_backwards(self):
        bob = new_test_user(self.env, login="bob_userg2", groups="base.group_user")
        t0 = datetime.now().replace(microsecond=0) + timedelta(minutes=1)
        with self.mock_datetime_and_now(t0):
            self.env["mail.presence"]._update_presence(bob)
        self.assertEqual(bob._get_im_status_version(), t0)
        gc_time = t0 + timedelta(seconds=PRESENCE_OUTDATED_TIMER + 1)
        with self.mock_datetime_and_now(gc_time):
            self.env["mail.presence"]._gc_bus_presence()
        self.assertEqual(bob._get_im_status_version(), t0)

    def test_im_status_invalidation(self):
        bob_user = new_test_user(self.env, login="bob_user")
        self.assertEqual(bob_user.im_status, "offline")
        self.env["mail.presence"]._update_presence(bob_user)
        self.assertEqual(bob_user.im_status, "online")

    def test_unlinking_sends_correct_im_status(self):
        bob = new_test_user(self.env, login="bob_userg", groups="base.group_user")
        self.env["mail.presence"]._update_presence(inactivity_period=0, user_or_guest=bob)
        unlink_time = datetime(2026, 1, 1, 10, 0, 0)
        expected_version = unlink_time.isoformat(timespec="microseconds")
        with self.assertBus(
            [
                BusResult(
                    (bob, "presence"),
                    "mail.record/insert",
                    {
                        "res.users": [
                            {
                                "id": bob.id,
                                "im_status": "offline",
                                "__version__": bob.write_date.isoformat(timespec="microseconds"),
                                "__field_versions__": {"im_status": expected_version},
                            },
                        ],
                    },
                ),
                BusResult(
                    bob,
                    "mail.record/insert",
                    {
                        "res.users": [
                            {
                                "id": bob.id,
                                "presence_status": "offline",
                                "__version__": bob.write_date.isoformat(timespec="microseconds"),
                                "__field_versions__": {"presence_status": expected_version},
                            },
                        ],
                    },
                ),
            ],
            show_store_versioning=True,
        ):
            with self.mock_datetime_and_now(unlink_time):
                self.env["mail.presence"].search([("user_id", "=", bob.id)]).unlink()

    def test_im_status_version_never_goes_backwards(self):
        bob = new_test_user(self.env, login="bob_userv", groups="base.group_user")
        t0 = datetime(2026, 1, 1, 10, 0, 0)
        with self.mock_datetime_and_now(t0):
            self.env["mail.presence"]._update_presence(bob)
        with self.mock_datetime_and_now(t0 + timedelta(minutes=5)):
            bob.manual_im_status = "busy"
        busy_version = bob._get_im_status_version()
        self.assertEqual(busy_version, t0 + timedelta(minutes=5))
        # a newer poll moves the version forward
        with self.mock_datetime_and_now(t0 + timedelta(minutes=7)):
            self.env["mail.presence"]._update_presence(bob)
        self.assertEqual(bob._get_im_status_version(), t0 + timedelta(minutes=7))
        # clearing the manual status after the poll moves it forward again
        with self.mock_datetime_and_now(t0 + timedelta(minutes=10)):
            bob.manual_im_status = False
        self.assertEqual(bob.im_status, "online")
        self.assertEqual(bob._get_im_status_version(), t0 + timedelta(minutes=10))

    def test_websocket_close_sends_offline_newer_than_manual_status(self):
        bob = new_test_user(self.env, login="bob_userw", groups="base.group_user")
        t0 = datetime(2026, 1, 1, 10, 0, 0)
        with self.mock_datetime_and_now(t0):
            self.env["mail.presence"]._update_presence(bob)
        with self.mock_datetime_and_now(t0 + timedelta(minutes=5)):
            bob.manual_im_status = "busy"
        close_time = t0 + timedelta(minutes=10)
        with self.assertBus(
            [
                BusResult(
                    (bob, "presence"),
                    "mail.record/insert",
                    {
                        "res.users": [
                            {
                                "id": bob.id,
                                "im_status": "offline",
                                "__version__": bob.write_date.isoformat(timespec="microseconds"),
                                "__field_versions__": {
                                    "im_status": close_time.isoformat(timespec="microseconds"),
                                },
                            },
                        ],
                    },
                ),
                BusResult(
                    bob,
                    "mail.record/insert",
                    {
                        "res.users": [
                            {
                                "id": bob.id,
                                "presence_status": "offline",
                                "__version__": bob.write_date.isoformat(timespec="microseconds"),
                                "__field_versions__": {
                                    "presence_status": close_time.isoformat(timespec="microseconds"),
                                },
                            },
                        ],
                    },
                ),
            ],
            show_store_versioning=True,
        ):
            with self.mock_datetime_and_now(close_time):
                self.env(user=bob)["ir.websocket"]._on_websocket_closed({"session_id": "A" * 84})

    def test_guest_without_presence_im_status_version_is_create_date(self):
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self.assertFalse(guest.presence_ids)
        store = Store().add(guest, "_store_im_status_fields")._build_result()
        data = store["mail.guest"][0]
        self.assertEqual(
            data["__field_versions__"]["im_status"],
            guest.create_date.isoformat(timespec="microseconds"),
        )

    def test_websocket_close_sends_offline_newer_for_guest(self):
        guest = self.env["mail.guest"].create({"name": "Guest"})
        t0 = datetime(2026, 1, 1, 10, 0, 0)
        with self.mock_datetime_and_now(t0):
            self.env["mail.presence"]._update_presence(guest)
        close_time = t0 + timedelta(minutes=10)
        cookies = {
            "session_id": "A" * 84,
            guest._cookie_name: guest._format_auth_cookie(),
        }
        with self.assertBus(
            [
                BusResult(
                    (guest, "presence"),
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            {
                                "id": guest.id,
                                "im_status": "offline",
                                "__version__": guest.write_date.isoformat(timespec="microseconds"),
                                "__field_versions__": {
                                    "im_status": close_time.isoformat(timespec="microseconds"),
                                },
                            },
                        ],
                    },
                ),
                BusResult(
                    guest,
                    "mail.record/insert",
                    {
                        "mail.guest": [
                            {
                                "id": guest.id,
                                "presence_status": "offline",
                                "__version__": guest.write_date.isoformat(timespec="microseconds"),
                                "__field_versions__": {
                                    "presence_status": close_time.isoformat(timespec="microseconds"),
                                },
                            },
                        ],
                    },
                ),
            ],
            show_store_versioning=True,
        ):
            with self.mock_datetime_and_now(close_time):
                self.env["ir.websocket"]._on_websocket_closed(cookies)
