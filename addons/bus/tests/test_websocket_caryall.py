# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gc
import json
from collections import defaultdict
from datetime import timedelta
from freezegun import freeze_time
from threading import Event
from unittest.mock import patch
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
    _websocket_instances
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
        gc.collect()
        first_ws = self.websocket_connect()
        second_ws = self.websocket_connect()
        self.assertEqual(len(_websocket_instances), 2)
        first_ws.close(CloseCode.CLEAN)
        second_ws.close(CloseCode.CLEAN)
        self.wait_remaining_websocket_connections()
        # serve_forever_patch prevent websocket instances from being
        # collected. Stop it now.
        self._serve_forever_patch.stop()
        gc.collect()
        self.assertEqual(len(_websocket_instances), 0)

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
        websocket.send(json.dumps({'event_name': 'subscribe'}))
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    def test_user_logout_incoming_message(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        websocket = self.websocket_connect(cookie=f'session_id={user_session.sid};')
        self.url_open('/web/session/logout')
        # The session with whom the websocket connected has been
        # deleted. WebSocket should disconnect in order for the
        # session to be updated.
        websocket.send(json.dumps({'event_name': 'subscribe'}))
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    def test_user_logout_outgoing_message(self):
        odoo_ws = None

        def patched_subscribe(self, *args):
            nonlocal odoo_ws
            odoo_ws = self

        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        websocket = self.websocket_connect(cookie=f'session_id={user_session.sid};')
        with patch.object(Websocket, 'subscribe', patched_subscribe):
            self.subscribe(
                websocket,
                ["channel1"],
                self.env["bus.bus"].search([], limit=1, order="id DESC").id or 0,
            )
            self.url_open('/web/session/logout')
            # Simulate postgres notify. The session with whom the websocket
            # connected has been deleted. WebSocket should be closed without
            # receiving the message.
            self.env['bus.bus']._sendone('channel1', 'notif type', 'message')
            odoo_ws.trigger_notification_dispatching()
            self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    def test_channel_subscription_disconnect(self):
        subscribe_done_event = Event()
        original_subscribe = dispatch.subscribe

        def patched_subscribe(*args):
            original_subscribe(*args)
            subscribe_done_event.set()

        with patch.object(dispatch, 'subscribe', patched_subscribe):
            websocket = self.websocket_connect()
            websocket.send(json.dumps({
                'event_name': 'subscribe',
                'data': {'channels': ['my_channel'], 'last': 0}
            }))
            subscribe_done_event.wait(timeout=5)
            # channel is added as expected to the channel to websocket map.
            self.assertIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)
            websocket.close(CloseCode.CLEAN)
            self.wait_remaining_websocket_connections()
            # channel is removed as expected when removing the last
            # websocket that was listening to this channel.
            self.assertNotIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)

    def test_channel_subscription_update(self):
        subscribe_done_event = Event()
        original_subscribe = dispatch.subscribe

        def patched_subscribe(*args):
            original_subscribe(*args)
            subscribe_done_event.set()

        with patch.object(dispatch, 'subscribe', patched_subscribe):
            websocket = self.websocket_connect()
            websocket.send(json.dumps({
                'event_name': 'subscribe',
                'data': {'channels': ['my_channel'], 'last': 0}
            }))
            subscribe_done_event.wait(timeout=5)
            subscribe_done_event.clear()
            # channel is added as expected to the channel to websocket map.
            self.assertIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)
            websocket.send(json.dumps({
                'event_name': 'subscribe',
                'data': {'channels': ['my_channel_2'], 'last': 0}
            }))
            subscribe_done_event.wait(timeout=5)
            # channel is removed as expected when updating the subscription.
            self.assertNotIn((self.env.registry.db_name, 'my_channel'), dispatch._channels_to_ws)

    def test_trigger_notification(self):
        original_subscribe = Websocket.subscribe
        odoo_ws = None

        def patched_subscribe(self, *args):
            nonlocal odoo_ws
            odoo_ws = self
            original_subscribe(self, *args)

        with patch.object(Websocket, 'subscribe', patched_subscribe):
            websocket = self.websocket_connect()
            self.env['bus.bus']._sendone('my_channel', 'notif_type', 'message')
            websocket.send(json.dumps({
                'event_name': 'subscribe',
                'data': {'channels': ['my_channel'], 'last': 0}
            }))

            notifications = json.loads(websocket.recv())
            self.assertEqual(1, len(notifications))
            self.assertEqual(notifications[0]['message']['type'], 'notif_type')
            self.assertEqual(notifications[0]['message']['payload'], 'message')

            self.env['bus.bus']._sendone('my_channel', 'notif_type', 'another_message')
            odoo_ws.trigger_notification_dispatching()

            notifications = json.loads(websocket.recv())
            # First notification has been received, we should only receive
            # the second one.
            self.assertEqual(1, len(notifications))
            self.assertEqual(notifications[0]['message']['type'], 'notif_type')
            self.assertEqual(notifications[0]['message']['payload'], 'another_message')

    def test_subscribe_higher_last_notification_id(self):
        subscribe_done_event = Event()
        server_last_notification_id = self.env['bus.bus'].sudo().search([], limit=1, order='id desc').id or 0
        client_last_notification_id = server_last_notification_id + 1

        def subscribe_side_effect(_, last):
            # Last notification id given by the client is higher than
            # the one known by the server, should default to 0.
            self.assertEqual(last, 0)
            subscribe_done_event.set()

        with patch.object(Websocket, 'subscribe', side_effect=subscribe_side_effect):
            websocket = self.websocket_connect()
            websocket.send(json.dumps({
                'event_name': 'subscribe',
                'data': {'channels': ['my_channel'], 'last': client_last_notification_id}
            }))
            subscribe_done_event.wait()

    def test_subscribe_lower_last_notification_id(self):
        subscribe_done_event = Event()
        server_last_notification_id = self.env['bus.bus'].sudo().search([], limit=1, order='id desc').id or 0
        client_last_notification_id = server_last_notification_id - 1

        def subscribe_side_effect(_, last):
            self.assertEqual(last, client_last_notification_id)
            subscribe_done_event.set()

        with patch.object(Websocket, 'subscribe', side_effect=subscribe_side_effect):
            websocket = self.websocket_connect()
            websocket.send(json.dumps({
                'event_name': 'subscribe',
                'data': {'channels': ['my_channel'], 'last': client_last_notification_id}
            }))
            subscribe_done_event.wait()

    def test_no_cursor_when_no_callback_for_lifecycle_event(self):
        with patch.object(Websocket, '_Websocket__event_callbacks', defaultdict(set)):
            with patch('odoo.addons.bus.websocket.acquire_cursor') as mock:
                self.websocket_connect()
                self.assertFalse(mock.called)
