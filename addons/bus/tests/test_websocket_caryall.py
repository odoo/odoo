# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gc
import json
from collections import defaultdict
from unittest.mock import patch
from weakref import WeakSet

try:
    import websocket as ws
except ImportError:
    ws = None

from odoo.api import Environment
from odoo.tests import new_test_user

from odoo.addons.bus import websocket as websocket_module
from odoo.addons.bus.models.bus import dispatch
from odoo.addons.bus.models.ir_websocket import IrWebsocket
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.websocket import (
    CloseCode,
    Websocket,
    WebsocketConnectionHandler,
)


class TestWebsocketCaryall(WebsocketCase):
    def test_lifecycle_hooks(self):
        events = []
        with patch.object(Websocket, '_Websocket__event_callbacks', defaultdict(set)):
            @Websocket.onopen
            def onopen(env, websocket):  # pylint: disable=unused-variable
                self.assertIsInstance(env, Environment)
                self.assertIsInstance(websocket, Websocket)
                events.append('open')

            @Websocket.onclose
            def onclose(env, websocket):  # pylint: disable=unused-variable
                self.assertIsInstance(env, Environment)
                self.assertIsInstance(websocket, Websocket)
                events.append('close')

            ws = self.websocket_connect()
            ws.close(CloseCode.CLEAN)
            self.wait_remaining_websocket_connections()
            self.assertEqual(events, ['open', 'close'])

    def test_instances_weak_set(self):
        with patch.object(websocket_module, "_websocket_instances", WeakSet()):
            first_ws = self.websocket_connect()
            second_ws = self.websocket_connect()
            self.assertEqual(len(websocket_module._websocket_instances), 2)
            first_ws.close(CloseCode.CLEAN)
            second_ws.close(CloseCode.CLEAN)
            self.wait_remaining_websocket_connections()
            # serve_forever_patch prevent websocket instances from being
            # collected. Stop it now.
            self._serve_forever_patch.stop()
            gc.collect()
            self.assertEqual(len(websocket_module._websocket_instances), 0)

    def test_channel_subscription_disconnect(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ['my_channel'], self.env['bus.bus']._bus_last_id())
        # channel is added as expected to the channel to websocket map.
        self.assertIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)
        websocket.close(CloseCode.CLEAN)
        self.wait_remaining_websocket_connections()
        # channel is removed as expected when removing the last
        # websocket that was listening to this channel.
        self.assertNotIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)

    def test_channel_subscription_update(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ['my_channel'], self.env['bus.bus']._bus_last_id())
        # channel is added as expected to the channel to websocket map.
        self.assertIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)
        self.subscribe(websocket, ['my_channel_2'], self.env['bus.bus']._bus_last_id())
        # channel is removed as expected when updating the subscription.
        self.assertNotIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)

    def test_trigger_notification(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ['my_channel'], self.env['bus.bus']._bus_last_id())
        self.env['bus.bus']._sendone('my_channel', 'notif_type', 'message')
        self.trigger_notification_dispatching()
        notifications = json.loads(websocket.recv())
        self.assertEqual(1, len(notifications))
        self.assertEqual(notifications[0]['message']['type'], 'notif_type')
        self.assertEqual(notifications[0]['message']['payload'], 'message')
        self.env['bus.bus']._sendone('my_channel', 'notif_type', 'another_message')
        self.trigger_notification_dispatching()
        notifications = json.loads(websocket.recv())
        # First notification has been received, we should only receive
        # the second one.
        self.assertEqual(1, len(notifications))
        self.assertEqual(notifications[0]['message']['type'], 'notif_type')
        self.assertEqual(notifications[0]['message']['payload'], 'another_message')

    def test_trigger_notification_unsupported_language(self):
        websocket = self.websocket_connect()
        # set session lang to what a websitor visitor could have (based on their
        # preferred language), this could be a unknown language (ex. territorial
        # specific) or a known language that is uninstalled; in all cases this
        # should not crash the notif. dispatching.
        self.update_session_context(lang='fr_LU')
        self.subscribe(websocket, ['my_channel'], self.env['bus.bus']._bus_last_id())
        self.env['bus.bus']._sendone('my_channel', 'notif_type', 'message')
        self.trigger_notification_dispatching()
        notifications = json.loads(websocket.recv())
        self.assertEqual(1, len(notifications))
        self.assertEqual(notifications[0]['message']['type'], 'notif_type')
        self.assertEqual(notifications[0]['message']['payload'], 'message')

    def test_subscribe_higher_last_notification_id(self):
        server_last_notification_id = self.env['bus.bus'].sudo().search([], limit=1, order='id desc').id or 0
        client_last_notification_id = server_last_notification_id + 1

        with patch.object(Websocket, 'subscribe', side_effect=Websocket.subscribe, autospec=True) as mock:
            websocket = self.websocket_connect()
            self.subscribe(websocket, ['my_channel'], client_last_notification_id)
            self.assertEqual(mock.call_args[0][2], 0)

    def test_subscribe_lower_last_notification_id(self):
        server_last_notification_id = self.env['bus.bus'].sudo().search([], limit=1, order='id desc').id or 0
        client_last_notification_id = server_last_notification_id - 1

        with patch.object(Websocket, 'subscribe', side_effect=Websocket.subscribe, autospec=True) as mock:
            websocket = self.websocket_connect()
            self.subscribe(websocket, ['my_channel'], client_last_notification_id)
            self.assertEqual(mock.call_args[0][2], client_last_notification_id)

    def test_subscribe_to_custom_channel(self):
        channel = new_test_user(self.env, "John")
        websocket = self.websocket_connect()
        with patch.object(IrWebsocket, "_build_bus_channel_list", return_value=[channel]):
            self.subscribe(websocket, [], self.env['bus.bus']._bus_last_id())
            channel._bus_send("notif_on_global_channel", "message")
            channel._bus_send("notif_on_private_channel", "message", subchannel="PRIVATE")
            self.trigger_notification_dispatching()
            notifications = json.loads(websocket.recv())
            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0]['message']['type'], 'notif_on_global_channel')
            self.assertEqual(notifications[0]['message']['payload'], 'message')

        with patch.object(IrWebsocket, "_build_bus_channel_list", return_value=[(channel, "PRIVATE")]):
            self.subscribe(websocket, [], self.env['bus.bus']._bus_last_id())
            channel._bus_send("notif_on_global_channel", "message")
            channel._bus_send("notif_on_private_channel", "message", subchannel="PRIVATE")
            self.trigger_notification_dispatching()
            notifications = json.loads(websocket.recv())
            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0]['message']['type'], 'notif_on_private_channel')
            self.assertEqual(notifications[0]['message']['payload'], 'message')

    def test_no_cursor_when_no_callback_for_lifecycle_event(self):
        with patch.object(Websocket, '_Websocket__event_callbacks', defaultdict(set)):
            with patch('odoo.addons.bus.websocket.acquire_cursor') as mock:
                self.websocket_connect()
                self.assertFalse(mock.called)

    def test_trigger_on_websocket_closed(self):
        with patch('odoo.addons.bus.models.ir_websocket.IrWebsocket._on_websocket_closed') as mock:
            ws = self.websocket_connect()
            ws.close(CloseCode.CLEAN)
            self.wait_remaining_websocket_connections()
            self.assertTrue(mock.called)

    def test_disconnect_when_version_outdated(self):
        # Outdated version, connection should be closed immediately
        with patch.object(WebsocketConnectionHandler, "_VERSION", "17.0-1"), patch.object(
            self, "_WEBSOCKET_URL", f"{self._BASE_WEBSOCKET_URL}?version=17.0-0",
        ):
            websocket = self.websocket_connect(
                ping_after_connect=False, header={"User-Agent": "Chrome/126.0.0.0"},
            )
            self.assert_close_with_code(websocket, CloseCode.CLEAN, "OUTDATED_VERSION")

        # Version not passed, User-Agent present, should be considered as outdated
        with patch.object(WebsocketConnectionHandler, "_VERSION", "17.0-1"), patch.object(
            self, "_WEBSOCKET_URL", self._BASE_WEBSOCKET_URL,
        ):
            websocket = self.websocket_connect(
                ping_after_connect=False, header={"User-Agent": "Chrome/126.0.0.0"},
            )
            self.assert_close_with_code(websocket, CloseCode.CLEAN, "OUTDATED_VERSION")
        # Version not passed, User-Agent not present, should not be considered
        # as outdated
        with patch.object(WebsocketConnectionHandler, "_VERSION", "17.0-1"), patch.object(
            self, "_WEBSOCKET_URL", self._BASE_WEBSOCKET_URL,
        ):
            websocket = self.websocket_connect()
            websocket.ping()
            websocket.recv_data_frame(control_frame=True)  # pong

    def test_websocket_check_outdated_subscription(self):
        self.env['bus.bus']._sendone('channel_A', 'some_notification', None)
        self.env['bus.bus']._sendone('channel_A', 'some_notification', None)
        self.trigger_notification_dispatching()
        last_id = self.env['bus.bus']._bus_last_id()
        self._reset_bus()
        websocket = self.websocket_connect()
        self.subscribe(websocket, ['channel_A'], last_id, check_outdated=True)
        message = json.loads(websocket.recv())[0]
        self.assertEqual(
            message,
            {'type': 'bus/subscription_outdated', 'internal': True, 'payload': None},
        )
        self.subscribe(websocket, ['channel_A'], last_id, check_outdated=False)
        with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
            websocket.recv()
