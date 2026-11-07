# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta

from odoo.tests import HttpCase, new_test_user
from ..models.mail_presence import PRESENCE_OUTDATED_TIMER
from odoo.addons.bus.models.bus import channel_with_db, json_dump


class TestMailPresence(HttpCase):
    def test_bus_presence_auto_vacuum(self):
        user = new_test_user(self.env, login="bob_user")
        more_than_away_timer_ago = datetime.now() - timedelta(seconds=PRESENCE_OUTDATED_TIMER + 1)
        more_than_away_timer_ago = more_than_away_timer_ago.replace(microsecond=0)
        with self.mock_datetime_and_now(more_than_away_timer_ago):
            self.env["mail.presence"]._update_presence(user)
        self.assertEqual(user.presence_ids.last_poll, more_than_away_timer_ago)
        self.env["mail.presence"]._gc_bus_presence()
        self.assertFalse(user.presence_ids)

    def test_im_status_invalidation(self):
        bob_user = new_test_user(self.env, login="bob_user")
        self.assertEqual(bob_user.im_status, "offline")
        self.env["mail.presence"]._update_presence(bob_user)
        self.assertEqual(bob_user.im_status, "online")

    def test_unlinking_sends_correct_im_status(self):
        bob = new_test_user(self.env, login="bob_userg", groups="base.group_user")
        self.env["mail.presence"]._update_presence(inactivity_period=0, user_or_guest=bob)
        unlink_time = datetime(2026, 1, 1, 10, 0, 0)
        with self.mock_datetime_and_now(unlink_time):
            self.env["mail.presence"].search([("user_id", "=", bob.id)]).unlink()
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        expected_version = unlink_time.isoformat(timespec="microseconds")
        presence_record = self._last_record((bob, "presence"), "res.users")
        self.assertEqual(presence_record["im_status"], "offline")
        self.assertEqual(presence_record["__field_versions__"]["im_status"], expected_version)
        user_record = self._last_record(bob, "res.users")
        self.assertEqual(user_record["presence_status"], "offline")
        self.assertEqual(user_record["__field_versions__"]["presence_status"], expected_version)

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
        with self.mock_datetime_and_now(close_time):
            self.env(user=bob)["ir.websocket"]._on_websocket_closed({"session_id": "A" * 84})
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        record = self._last_record((bob, "presence"), "res.users")
        self.assertEqual(record["im_status"], "offline")
        version = record["__field_versions__"]["im_status"]
        self.assertEqual(version, close_time.isoformat(timespec="microseconds"))

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
        with self.mock_datetime_and_now(close_time):
            self.env["ir.websocket"]._on_websocket_closed(cookies)
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        record = self._last_record((guest, "presence"), "mail.guest")
        self.assertEqual(record["im_status"], "offline")
        version = record["__field_versions__"]["im_status"]
        self.assertEqual(version, close_time.isoformat(timespec="microseconds"))

    def _last_record(self, channel, model):
        channel = json_dump(channel_with_db(self.env.cr.dbname, channel))
        notif = self.env["bus.bus"].sudo().search(
            [("channel", "=", channel)], order="id desc", limit=1,
        )
        return json.loads(notif.message)["payload"][model][0]
