# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gc
import json
import os
from collections import defaultdict
from datetime import timedelta
from freezegun import freeze_time
from threading import Event
from unittest.mock import patch
from weakref import WeakSet

from odoo import http
from odoo.api import Environment
from odoo.tests import common, new_test_user
from odoo.tools import mute_logger
from .common import WebsocketCase
from .. import websocket as websocket_module
from ..models.bus import dispatch
from ..models.ir_websocket import IrWebsocket
from ..websocket import (
    CloseCode,
    Frame,
    Opcode,
    TimeoutManager,
    Websocket,
    WebsocketConnectionHandler,
)

@common.tagged('post_install', '-at_install')
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

    def test_timeout_manager_no_response_timeout(self):
        with freeze_time('2022-08-19') as frozen_time:
            timeout_manager = TimeoutManager()
            # A PING frame was just sent, if no pong has been received
            # within TIMEOUT seconds, the connection should have timed out.
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.PING))
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertFalse(timeout_manager.has_frame_response_timed_out())
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertTrue(timeout_manager.has_frame_response_timed_out())

            timeout_manager = TimeoutManager()
            # A CLOSE frame was just sent, if no close has been received
            # within TIMEOUT seconds, the connection should have timed out.
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.CLOSE))
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertFalse(timeout_manager.has_frame_response_timed_out())
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertTrue(timeout_manager.has_frame_response_timed_out())

    def test_timeout_manager_overlapping_timeouts(self):
        with freeze_time('2022-08-19') as frozen_time:
            timeout_manager = TimeoutManager()
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.CLOSE))
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.PING))
            timeout_manager.acknowledge_frame_receipt(Frame(Opcode.PONG))
            frozen_time.tick(delta=timedelta(seconds=timeout_manager.TIMEOUT + 1))
            self.assertTrue(timeout_manager.has_frame_response_timed_out())

    def test_timeout_manager_keep_alive_timeout(self):
        with freeze_time('2022-08-19') as frozen_time:
            timeout_manager = TimeoutManager()
            frozen_time.tick(delta=timedelta(seconds=timeout_manager._keep_alive_timeout / 2))
            self.assertFalse(timeout_manager.has_keep_alive_timed_out())
            frozen_time.tick(delta=timedelta(seconds=timeout_manager._keep_alive_timeout / 2 + 1))
            self.assertTrue(timeout_manager.has_keep_alive_timed_out())

    def test_timeout_manager_reset_wait_for(self):
        with freeze_time('2022-08-19') as frozen_time:
            timeout_manager = TimeoutManager()
            # PING frame
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.PING))
            timeout_manager.acknowledge_frame_receipt(Frame(Opcode.PONG))
            frozen_time.tick(delta=timedelta(seconds=timeout_manager.TIMEOUT + 1))
            self.assertFalse(timeout_manager.has_frame_response_timed_out())

            # CLOSE frame
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.CLOSE))
            timeout_manager.acknowledge_frame_receipt(Frame(Opcode.CLOSE))
            frozen_time.tick(delta=timedelta(seconds=timeout_manager.TIMEOUT + 1))
            self.assertFalse(timeout_manager.has_frame_response_timed_out())

    def test_user_login(self):
        websocket = self.websocket_connect()
        new_test_user(self.env, login='test_user', password='Password!1')
        self.authenticate('test_user', 'Password!1')
        # The session with whom the websocket connected has been
        # deleted. WebSocket should disconnect in order for the
        # session to be updated.
        self.subscribe(websocket, wait_for_dispatch=False)
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    def test_user_logout_incoming_message(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        websocket = self.websocket_connect(cookie=f'session_id={user_session.sid};')
        self.url_open('/web/session/logout')
        # The session with whom the websocket connected has been
        # deleted. WebSocket should disconnect in order for the
        # session to be updated.
        self.subscribe(websocket, wait_for_dispatch=False)
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    def test_user_logout_outgoing_message(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        websocket = self.websocket_connect(cookie=f'session_id={user_session.sid};')
        self.subscribe(websocket, ['channel1'], self.env['bus.bus']._bus_last_id())
        self.url_open('/web/session/logout')
        # Simulate postgres notify. The session with whom the websocket
        # connected has been deleted. WebSocket should be closed without
        # receiving the message.
        self.env['bus.bus']._sendone('channel1', 'notif type', 'message')
        self.trigger_notification_dispatching(["channel1"])
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

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
        self.trigger_notification_dispatching(["my_channel"])
        notifications = json.loads(websocket.recv())
        self.assertEqual(1, len(notifications))
        self.assertEqual(notifications[0]['message']['type'], 'notif_type')
        self.assertEqual(notifications[0]['message']['payload'], 'message')
        self.env['bus.bus']._sendone('my_channel', 'notif_type', 'another_message')
        self.trigger_notification_dispatching(["my_channel"])
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
        self.session.context['lang'] = 'fr_LU'
        http.root.session_store.save(self.session)
        self.subscribe(websocket, ['my_channel'], self.env['bus.bus']._bus_last_id())
        self.env['bus.bus']._sendone('my_channel', 'notif_type', 'message')
        self.trigger_notification_dispatching(["my_channel"])
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
        channel = self.env["res.partner"].create({"name": "John"})
        websocket = self.websocket_connect()
        with patch.object(IrWebsocket, "_build_bus_channel_list", return_value=[channel]):
            self.subscribe(websocket, [], self.env['bus.bus']._bus_last_id())
            channel._bus_send("notif_on_global_channel", "message")
            channel._bus_send("notif_on_private_channel", "message", subchannel="PRIVATE")
            self.trigger_notification_dispatching([channel, (channel, "PRIVATE")])
            notifications = json.loads(websocket.recv())
            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0]['message']['type'], 'notif_on_global_channel')
            self.assertEqual(notifications[0]['message']['payload'], 'message')

        with patch.object(IrWebsocket, "_build_bus_channel_list", return_value=[(channel, "PRIVATE")]):
            self.subscribe(websocket, [], self.env['bus.bus']._bus_last_id())
            channel._bus_send("notif_on_global_channel", "message")
            channel._bus_send("notif_on_private_channel", "message", subchannel="PRIVATE")
            self.trigger_notification_dispatching([channel, (channel, "PRIVATE")])
            notifications = json.loads(websocket.recv())
            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0]['message']['type'], 'notif_on_private_channel')
            self.assertEqual(notifications[0]['message']['payload'], 'message')

    def test_no_cursor_when_no_callback_for_lifecycle_event(self):
        with patch.object(Websocket, '_Websocket__event_callbacks', defaultdict(set)):
            with patch('odoo.addons.bus.websocket.acquire_cursor') as mock:
                self.websocket_connect()
                self.assertFalse(mock.called)

    @patch.dict(os.environ, {"ODOO_BUS_PUBLIC_SAMESITE_WS": "True"})
    def test_public_configuration(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        serve_forever_called_event = Event()
        original_serve_forever = WebsocketConnectionHandler._serve_forever

        def serve_forever(websocket, *args):
            original_serve_forever(websocket, *args)
            self.assertNotEqual(websocket._session.sid, user_session.sid)
            self.assertNotEqual(websocket._session.uid, user_session.uid)
            serve_forever_called_event.set()

        with patch.object(
            WebsocketConnectionHandler, '_serve_forever', side_effect=serve_forever
        ) as mock, mute_logger('odoo.addons.bus.websocket'):
            ws = self.websocket_connect(
                cookie=f'session_id={user_session.sid};',
                origin="http://example.com"
            )
            self.assertTrue(
                ws.getheaders().get('set-cookie').startswith(f'session_id={user_session.sid}'),
                'The set-cookie response header must be the origin request session rather than the websocket session'
            )
            serve_forever_called_event.wait(timeout=5)
            self.assertTrue(mock.called)

    def test_trigger_on_websocket_closed(self):
        with patch('odoo.addons.bus.models.ir_websocket.IrWebsocket._on_websocket_closed') as mock:
            ws = self.websocket_connect()
            ws.close(CloseCode.CLEAN)
            self.wait_remaining_websocket_connections()
            self.assertTrue(mock.called)

    def test_disconnect_when_version_outdated(self):
        # Outdated version, connection should be closed immediately
        with patch.object(WebsocketConnectionHandler, "_VERSION", "17.0-1"), patch.object(
            self, "_WEBSOCKET_URL", f"{self._BASE_WEBSOCKET_URL}?version=17.0-0"
        ):
            websocket = self.websocket_connect(
                ping_after_connect=False, header={"User-Agent": "Chrome/126.0.0.0"}
            )
            self.assert_close_with_code(websocket, CloseCode.CLEAN, "OUTDATED_VERSION")

        # Version not passed, User-Agent present, should be considered as outdated
        with patch.object(WebsocketConnectionHandler, "_VERSION", "17.0-1"), patch.object(
            self, "_WEBSOCKET_URL", self._BASE_WEBSOCKET_URL
        ):
            websocket = self.websocket_connect(
                ping_after_connect=False, header={"User-Agent": "Chrome/126.0.0.0"}
            )
            self.assert_close_with_code(websocket, CloseCode.CLEAN, "OUTDATED_VERSION")
        # Version not passed, User-Agent not present, should not be considered
        # as outdated
        with patch.object(WebsocketConnectionHandler, "_VERSION", "17.0-1"), patch.object(
            self, "_WEBSOCKET_URL", self._BASE_WEBSOCKET_URL
        ):
            websocket = self.websocket_connect()
            websocket.ping()
            websocket.recv_data_frame(control_frame=True)  # pong

    def test_websocket_terminates_after_closing_timeout(self):
        orig_disconnect = Websocket.disconnect
        orig_terminate = Websocket._terminate
        disconnect_done_event = Event()
        terminate_done_event = Event()

        def disconnect_wrapper(self, code):
            orig_disconnect(self, code)
            disconnect_done_event.set()

        def terminate_wrapper(self):
            orig_terminate(self)
            terminate_done_event.set()

        with (
            patch('odoo.addons.bus.websocket.TimeoutManager.KEEP_ALIVE_TIMEOUT', 0),
            patch.object(Websocket, 'disconnect', disconnect_wrapper),
            patch.object(Websocket, '_terminate', terminate_wrapper),
            freeze_time('2022-08-19') as frozen_time,
        ):
            ws = self.websocket_connect(ping_after_connect=False)
            ws.send(b'\x00')  # Wake up the WebSocket loop.
            self.assertTrue(
                disconnect_done_event.wait(timeout=5),
                'Server should have initiated the closing handshake as the keep alive timeout is exceeded.',
            )
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT + 1))
            ws.send(b'\x00')  # Wake up the WebSocket loop.
            self.assertTrue(
                terminate_done_event.wait(timeout=5),
                'Server should have terminated the connection as it didn\'t receive any response.',
            )
