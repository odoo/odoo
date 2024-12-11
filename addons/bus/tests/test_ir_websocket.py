# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, timedelta
from freezegun import freeze_time
try:
    import websocket as ws
except ImportError:
    ws = None

from odoo.tests import new_test_user, tagged
from .common import WebsocketCase
from ..models.bus_presence import AWAY_TIMER
from ..models.bus import channel_with_db, json_dump


@tagged("-at_install", "post_install")
class TestIrWebsocket(WebsocketCase):
    def test_only_allow_string_channels_from_frontend(self):
        with self.assertRaises(ValueError):
            self.env['ir.websocket']._subscribe({
                'inactivity_period': 1000,
                'last': 0,
                'channels': [('odoo', 'discuss.channel', 5)],
            })

    def test_notify_on_status_change(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        session = self.authenticate("bob_user", "bob_user")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(
            websocket,
            [f"odoo-presence-res.partner_{bob.partner_id.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        # offline => online
        self.env["bus.presence"]._update_presence(
            inactivity_period=0, identity_field="user_id", identity_value=bob.id
        )
        self.trigger_notification_dispatching([(bob.partner_id, "presence")])
        message = json.loads(websocket.recv())[0]["message"]
        self.assertEqual(message["type"], "bus.bus/im_status_updated")
        self.assertEqual(message["payload"]["im_status"], "online")
        self.assertEqual(message["payload"]["partner_id"], bob.partner_id.id)
        # online => away
        away_timer_later = datetime.now() + timedelta(seconds=AWAY_TIMER + 1)
        with freeze_time(away_timer_later):
            self.env["bus.presence"]._update_presence(
                inactivity_period=(AWAY_TIMER + 1) * 1000,
                identity_field="user_id",
                identity_value=bob.id,
            )
            self.trigger_notification_dispatching([(bob.partner_id, "presence")])
            message = json.loads(websocket.recv())[0]["message"]
            self.assertEqual(message["type"], "bus.bus/im_status_updated")
            self.assertEqual(message["payload"]["im_status"], "away")
            self.assertEqual(message["payload"]["partner_id"], bob.partner_id.id)
        # away => online
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            self.env["bus.presence"]._update_presence(
                inactivity_period=0, identity_field="user_id", identity_value=bob.id
            )
            self.trigger_notification_dispatching([(bob.partner_id, "presence")])
            message = json.loads(websocket.recv())[0]["message"]
            self.assertEqual(message["type"], "bus.bus/im_status_updated")
            self.assertEqual(message["payload"]["im_status"], "online")
            self.assertEqual(message["payload"]["partner_id"], bob.partner_id.id)
        # online => online, nothing happens
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            self.env["bus.presence"]._update_presence(
                inactivity_period=0, identity_field="user_id", identity_value=bob.id
            )
            self.trigger_notification_dispatching([(bob.partner_id, "presence")])
            timeout_occurred = False
            # Save point rollback of `assertRaises` can compete with `on_websocket_close`
            # leading to `InvalidSavepoint` errors. We need to avoid it.
            try:
                websocket.recv()
            except ws._exceptions.WebSocketTimeoutException:
                timeout_occurred = True
            self.assertTrue(timeout_occurred)

    def test_receive_missed_presences_on_subscribe(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        session = self.authenticate("bob_user", "bob_user")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.env["bus.presence"].create({"user_id": bob.id, "status": "online"})
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.subscribe(
            websocket,
            [f"odoo-presence-res.partner_{bob.partner_id.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        self.trigger_notification_dispatching([bob.partner_id])
        notification = json.loads(websocket.recv())[0]
        self._close_websockets()
        bus_record = self.env["bus.bus"].search([("id", "=", int(notification["id"]))])
        self.assertEqual(
            bus_record.channel,
            json_dump(channel_with_db(self.env.cr.dbname, bob.partner_id)),
        )
        self.assertEqual(notification["message"]["type"], "bus.bus/im_status_updated")
        self.assertEqual(notification["message"]["payload"]["im_status"], "online")
        self.assertEqual(notification["message"]["payload"]["partner_id"], bob.partner_id.id)
