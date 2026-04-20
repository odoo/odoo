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
        self.trigger_notification_dispatching([(bob, "presence")])
        message = json.loads(websocket.recv())[0]["message"]
        self.assertEqual(message["type"], "mail.record/insert")
        self.assertEqual(message["payload"]["res.users"][0]["im_status"], "online")
        self.assertEqual(message["payload"]["res.users"][0]["id"], bob.id)
        # online => away
        away_timer_later = datetime.now() + timedelta(seconds=AWAY_TIMER + 1)
        with freeze_time(away_timer_later):
            self.env["mail.presence"]._update_presence(bob, (AWAY_TIMER + 1) * 1000)
            self.trigger_notification_dispatching([(bob, "presence")])
            message = json.loads(websocket.recv())[0]["message"]
            self.assertEqual(message["type"], "mail.record/insert")
            self.assertEqual(message["payload"]["res.users"][0]["im_status"], "away")
            self.assertEqual(message["payload"]["res.users"][0]["id"], bob.id)
        # away => online
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            self.env["mail.presence"]._update_presence(bob)
            self.trigger_notification_dispatching([(bob, "presence")])
            message = json.loads(websocket.recv())[0]["message"]
            self.assertEqual(message["type"], "mail.record/insert")
            self.assertEqual(message["payload"]["res.users"][0]["im_status"], "online")
            self.assertEqual(message["payload"]["res.users"][0]["id"], bob.id)
        # online => online, nothing happens
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            self.env["mail.presence"]._update_presence(bob)
            self.trigger_notification_dispatching([(bob, "presence")])
            timeout_occurred = False
            # Save point rollback of `assertRaises` can compete with `on_websocket_close`
            # leading to `InvalidSavepoint` errors. We need to avoid it.
            try:
                websocket.recv()
            except ws._exceptions.WebSocketTimeoutException:
                timeout_occurred = True
            self.assertTrue(timeout_occurred)
