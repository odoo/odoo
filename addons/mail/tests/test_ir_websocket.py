# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime, timedelta
from freezegun import freeze_time
try:
    import websocket as ws
except ImportError:
    ws = None

from odoo.tests import new_test_user

from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.mail.models.mail_presence import AWAY_TIMER


class TestIrWebsocket(WebsocketCase):
    def _assert_presence_notified(self, websocket, user, status):
        """Assert both notifications of a presence change are received.

        A presence change notifies two distinct channels: the presence channel
        of the user (``im_status``) and its record channel (``presence_status``).
        The dispatcher sends one frame per channel, in the iteration order of a
        set of topics, which is not guaranteed: gather both notifications and
        key them by their field rather than relying on arrival order. Consuming
        both also matters, as any frame left behind would be picked up by a
        later ``recv``.
        """
        notifications = []
        while len(notifications) < 2:
            notifications += json.loads(websocket.recv())
        payload_by_field = {}
        for notification in notifications:
            message = notification["message"]
            self.assertEqual(message["type"], "mail.record/insert")
            payload = message["payload"]["res.users"][0]
            field = "im_status" if "im_status" in payload else "presence_status"
            payload_by_field[field] = payload
        self.assertEqual(payload_by_field.keys(), {"im_status", "presence_status"})
        for field, payload in payload_by_field.items():
            self.assertEqual(payload["id"], user.id)
            self.assertEqual(payload[field], status)

    def test_notify_on_status_change(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        session = self.authenticate("bob_user", "bob_user")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(
            websocket,
            [f"odoo-presence-res.users_{bob.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        # offline => online
        self.env["mail.presence"]._update_presence(bob)
        self.trigger_notification_dispatching()
        self._assert_presence_notified(websocket, bob, "online")
        # online => away
        away_timer_later = datetime.now() + timedelta(seconds=AWAY_TIMER + 1)
        with freeze_time(away_timer_later):
            self.env["mail.presence"]._update_presence(bob, (AWAY_TIMER + 1) * 1000)
            self.trigger_notification_dispatching()
            self._assert_presence_notified(websocket, bob, "away")
        # away => online
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            self.env["mail.presence"]._update_presence(bob)
            self.trigger_notification_dispatching()
            self._assert_presence_notified(websocket, bob, "online")
        # online => online, nothing happens
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            self.env["mail.presence"]._update_presence(bob)
            self.trigger_notification_dispatching()
            timeout_occurred = False
            # Save point rollback of `assertRaises` can compete with `on_websocket_close`
            # leading to `InvalidSavepoint` errors. We need to avoid it.
            try:
                websocket.recv()
            except ws._exceptions.WebSocketTimeoutException:
                timeout_occurred = True
            self.assertTrue(timeout_occurred)

    def test_subscribe_discuss_category_without_token(self):
        new_test_user(self.env, login="bob_user", groups="base.group_user")
        session = self.authenticate("bob_user", "bob_user")
        category = self.env["discuss.category"].create({"name": "favorites"})
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(
            websocket,
            [f"discuss.category_{category.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        category._bus_send("sanity_check", None)
        self.trigger_notification_dispatching()
        notifications = json.loads(websocket.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "sanity_check")
