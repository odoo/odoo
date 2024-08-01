# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, timedelta
from freezegun import freeze_time
try:
    import websocket as ws
except ImportError:
    websocket = None

from odoo.tests import new_test_user, tagged
from .common import WebsocketCase
from ..models.bus_presence import AWAY_TIMER


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
        group_user = self.env.ref("base.group_user")
        session = self.authenticate("bob_user", "bob_user")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(websocket, [], self.env["bus.bus"]._bus_last_id())
        # offline => online
        websocket.send(
            json.dumps(
                {
                    "event_name": "update_presence",
                    "data": {"inactivity_period": 0, "im_status_ids_by_model": {}},
                }
            )
        )
        self.trigger_notification_dispatching([group_user])
        message = json.loads(websocket.recv())[0]["message"]
        self.assertEqual(message["type"], "bus.bus/im_status_updated")
        self.assertEqual(message["payload"]["im_status"], "online")
        self.assertEqual(message["payload"]["partner_id"], bob.partner_id.id)
        # online => away
        away_timer_later = datetime.now() + timedelta(seconds=AWAY_TIMER + 1)
        with freeze_time(away_timer_later):
            websocket.send(
                json.dumps(
                    {
                        "event_name": "update_presence",
                        "data": {
                            "inactivity_period": (AWAY_TIMER + 1) * 1000,
                            "im_status_ids_by_model": {},
                        },
                    }
                )
            )
            self.trigger_notification_dispatching([group_user])
            message = json.loads(websocket.recv())[0]["message"]
            self.assertEqual(message["type"], "bus.bus/im_status_updated")
            self.assertEqual(message["payload"]["im_status"], "away")
            self.assertEqual(message["payload"]["partner_id"], bob.partner_id.id)
        # away => online
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            websocket.send(
                json.dumps(
                    {
                        "event_name": "update_presence",
                        "data": {"inactivity_period": 0, "im_status_ids_by_model": {}},
                    }
                )
            )
            self.trigger_notification_dispatching([self.env.ref("base.group_user")])
            message = json.loads(websocket.recv())[0]["message"]
            self.assertEqual(message["type"], "bus.bus/im_status_updated")
            self.assertEqual(message["payload"]["im_status"], "online")
            self.assertEqual(message["payload"]["partner_id"], bob.partner_id.id)
        # online => online, nothing happens
        ten_minutes_later = datetime.now() + timedelta(minutes=10)
        with freeze_time(ten_minutes_later):
            websocket.send(
                json.dumps(
                    {
                        "event_name": "update_presence",
                        "data": {"inactivity_period": 0, "im_status_ids_by_model": {}},
                    }
                )
            )
            self.trigger_notification_dispatching([group_user])
            with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
                message = json.loads(websocket.recv())[0]["message"]
