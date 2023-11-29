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
try:
    from websocket._exceptions import WebSocketBadStatusException
except ImportError:
    pass

from odoo.api import Environment
from odoo.tests import common, new_test_user
from .common import WebsocketCase
from ..models.bus import dispatch
from ..websocket import (
    CloseCode,
    Frame,
    Opcode,
    TimeoutManager,
    TimeoutReason,
    Websocket,
    WebsocketConnectionHandler,
)

@common.tagged('post_install', '-at_install')
class TestWebsocketCaryall(WebsocketCase):
    def test_lifecycle_hooks(self):
        events = []
        with patch.object(Websocket, '_event_callbacks', defaultdict(set)):
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
        with patch.object(Websocket, "_instances", WeakSet()):
            first_ws = self.websocket_connect()
            second_ws = self.websocket_connect()
            self.assertEqual(len(Websocket._instances), 2)
            first_ws.close(CloseCode.CLEAN)
            second_ws.close(CloseCode.CLEAN)
            self.wait_remaining_websocket_connections()
            # serve_forever_patch prevent websocket instances from being
            # collected. Stop it now.
            self._serve_forever_patch.stop()
            gc.collect()
            self.assertEqual(len(Websocket._instances), 0)

    def test_timeout_manager_no_response_timeout(self):
        with freeze_time('2022-08-19') as frozen_time:
            timeout_manager = TimeoutManager()
            # A PING frame was just sent, if no pong has been received
            # within TIMEOUT seconds, the connection should have timed out.
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.PING))
            self.assertEqual(timeout_manager._awaited_opcode, Opcode.PONG)
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertFalse(timeout_manager.has_timed_out())
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertTrue(timeout_manager.has_timed_out())
            self.assertEqual(timeout_manager.timeout_reason, TimeoutReason.NO_RESPONSE)

            timeout_manager = TimeoutManager()
            # A CLOSE frame was just sent, if no close has been received
            # within TIMEOUT seconds, the connection should have timed out.
            timeout_manager.acknowledge_frame_sent(Frame(Opcode.CLOSE))
            self.assertEqual(timeout_manager._awaited_opcode, Opcode.CLOSE)
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertFalse(timeout_manager.has_timed_out())
            frozen_time.tick(delta=timedelta(seconds=TimeoutManager.TIMEOUT / 2))
            self.assertTrue(timeout_manager.has_timed_out())
            self.assertEqual(timeout_manager.timeout_reason, TimeoutReason.NO_RESPONSE)

    def test_timeout_manager_keep_alive_timeout(self):
        with freeze_time('2022-08-19') as frozen_time:
            timeout_manager = TimeoutManager()
            frozen_time.tick(delta=timedelta(seconds=timeout_manager._keep_alive_timeout / 2))
            self.assertFalse(timeout_manager.has_timed_out())
            frozen_time.tick(delta=timedelta(seconds=timeout_manager._keep_alive_timeout / 2 + 1))
            self.assertTrue(timeout_manager.has_timed_out())
            self.assertEqual(timeout_manager.timeout_reason, TimeoutReason.KEEP_ALIVE)

    def test_timeout_manager_reset_wait_for(self):
        timeout_manager = TimeoutManager()
        # PING frame
        timeout_manager.acknowledge_frame_sent(Frame(Opcode.PING))
        self.assertEqual(timeout_manager._awaited_opcode, Opcode.PONG)
        timeout_manager.acknowledge_frame_receipt(Frame(Opcode.PONG))
        self.assertIsNone(timeout_manager._awaited_opcode)

        # CLOSE frame
        timeout_manager.acknowledge_frame_sent(Frame(Opcode.CLOSE))
        self.assertEqual(timeout_manager._awaited_opcode, Opcode.CLOSE)
        timeout_manager.acknowledge_frame_receipt(Frame(Opcode.CLOSE))
        self.assertIsNone(timeout_manager._awaited_opcode)

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

    def test_no_cursor_when_no_callback_for_lifecycle_event(self):
        with patch.object(Websocket, '_event_callbacks', defaultdict(set)):
            with patch('odoo.addons.bus.websocket.acquire_cursor') as mock:
                self.websocket_connect()
                self.assertFalse(mock.called)

    @patch.dict(os.environ, {"ODOO_BUS_PUBLIC_SAMESITE_WS": "True"})
    def test_public_configuration(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        serve_forever_called_event = Event()

        def serve_forever(websocket, *args):
            self.assertNotEqual(websocket._session.sid, user_session.sid)
            self.assertNotEqual(websocket._session.uid, user_session.uid)
            serve_forever_called_event.set()

        with patch.object(WebsocketConnectionHandler, '_serve_forever', side_effect=serve_forever) as mock:
            self.websocket_connect(
                cookie=f'session_id={user_session.sid};',
                origin="http://example.com"
            )
            serve_forever_called_event.wait(timeout=5)
            self.assertTrue(mock.called)
