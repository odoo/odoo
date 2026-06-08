# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from threading import Event
from unittest.mock import patch

from freezegun import freeze_time

from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.websocket import Frame, Opcode, TimeoutManager, Websocket


class TestWebsocketTimeouts(WebsocketCase):
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

    def test_websocket_terminates_after_closing_timeout(self):
        orig_disconnect = Websocket._disconnect
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
            patch.object(Websocket, '_disconnect', disconnect_wrapper),
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
