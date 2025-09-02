# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import struct
from threading import Event
import unittest
from unittest.mock import patch
import inspect
from werkzeug.exceptions import BadRequest
import contextlib

try:
    import websocket
except ImportError:
    websocket = None

from odoo.http import request
from odoo.tests.common import HOST, release_test_lock, TEST_CURSOR_COOKIE_NAME, Like, _registry_test_lock
from odoo.tests import HttpCase
from ..websocket import CloseCode, Websocket, WebsocketConnectionHandler
from ..models.bus import dispatch, hashable, channel_with_db


class WebsocketCase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if websocket is None:
            cls._logger.warning("websocket-client module is not installed")
            raise unittest.SkipTest("websocket-client module is not installed")
        cls._BASE_WEBSOCKET_URL = f"ws://{HOST}:{cls.http_port()}/websocket"
        cls._WEBSOCKET_URL = f"{cls._BASE_WEBSOCKET_URL}?version={WebsocketConnectionHandler._VERSION}"
        websocket_allowed_patch = patch.object(WebsocketConnectionHandler, "websocket_allowed", return_value=True)
        cls.startClassPatcher(websocket_allowed_patch)

    def setUp(self):
        super().setUp()
        self._websockets = set()
        # Used to ensure websocket connections have been closed
        # properly.
        self._websocket_events = set()
        original_serve_forever = WebsocketConnectionHandler._serve_forever

        def _mocked_serve_forever(*args):
            websocket_closed_event = Event()
            self._websocket_events.add(websocket_closed_event)
            original_serve_forever(*args)
            websocket_closed_event.set()

        self._serve_forever_patch = patch.object(
            WebsocketConnectionHandler,
            '_serve_forever',
            wraps=_mocked_serve_forever
        )
        self.startPatcher(self._serve_forever_patch)
        self.enterContext(release_test_lock())  # Release the lock during websocket tests
        self.http_request_key = 'websocket'

    def tearDown(self):
        self._close_websockets()
        super().tearDown()

    def _close_websockets(self):
        """
        Close all the connected websockets and wait for the connection
        to terminate.
        """
        for ws in self._websockets:
            if ws.connected:
                ws.close(CloseCode.CLEAN)
        self.wait_remaining_websocket_connections()

    @contextlib.contextmanager
    def allow_requests(self, *args, **kwargs):
        # As the lock is always unlocked, we reacquire it before allowing request
        # to avoid exceptions.
        with _registry_test_lock, super().allow_requests(*args, **kwargs):
            yield

    def assertCanOpenTestCursor(self):
        # As the lock is always unlocked during WebsocketCases we have a whitelist of
        # methods which must match. We also default to super if we are coming from a cursor.
        allowed_methods = [  # function + filename
            ('acquire_cursor', Like('.../bus/websocket.py')),
        ]
        if any(
            frame.function == function and frame.filename == filename
            for frame in inspect.stack()
            for function, filename in allowed_methods
        ) or request:
            return super().assertCanOpenTestCursor()
        raise BadRequest('Opening a cursor from an unknown method in websocket test.')

    def websocket_connect(self, *args, ping_after_connect=True, **kwargs):
        """
        Connect a websocket. If no cookie is given, the connection is
        opened with a default session. The created websocket is closed
        at the end of the test.
        """
        if 'cookie' not in kwargs:
            self.session = self.authenticate(None, None)
            kwargs['cookie'] = f'session_id={self.session.sid}'
        kwargs['timeout'] = 10  # keep a large timeout to avoid aving a websocket request escaping the test
        # The cursor lock is already released, we just need to pass the right cookie.
        kwargs['cookie'] += f';{TEST_CURSOR_COOKIE_NAME}={self.http_request_key}'
        ws = websocket.create_connection(
            self._WEBSOCKET_URL, *args, **kwargs
        )
        if ping_after_connect:
            ws.ping()
            ws.recv_data_frame(control_frame=True)  # pong
        self._websockets.add(ws)
        return ws

    def subscribe(self, websocket, channels=None, last=None, wait_for_dispatch=True):
        """ Subscribe the websocket to the given channels.

        :param websocket: The websocket of the client.
        :param channels: The list of channels to subscribe to.
        :param last: The last notification id the client received.
        :param wait_for_dispatch: Whether to wait for the notification
            dispatching trigerred by the subscription.
        """
        dispatch_bus_notification_done = Event()
        original_dispatch_bus_notifications = Websocket._dispatch_bus_notifications

        def _mocked_dispatch_bus_notifications(self, *args):
            original_dispatch_bus_notifications(self, *args)
            dispatch_bus_notification_done.set()

        with patch.object(Websocket, '_dispatch_bus_notifications', _mocked_dispatch_bus_notifications):
            sub = {'event_name': 'subscribe', 'data': {
                'channels': channels or [],
            }}
            if last is not None:
                sub['data']['last'] = last
            websocket.send(json.dumps(sub))
            if wait_for_dispatch:
                dispatch_bus_notification_done.wait(timeout=5)

    def trigger_notification_dispatching(self, channels):
        """ Notify the websockets subscribed to the given channels that new
        notifications are available. Usefull since the bus is not able to do
        it during tests.
        """
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        channels = [
            hashable(channel_with_db(self.registry.db_name, c)) for c in channels
        ]
        websockets = set()
        for channel in channels:
            websockets.update(dispatch._channels_to_ws.get(hashable(channel), []))
        for websocket in websockets:
            websocket.trigger_notification_dispatching()

    def wait_remaining_websocket_connections(self):
        """ Wait for the websocket connections to terminate. """
        for event in self._websocket_events:
            event.wait(5)

    def assert_close_with_code(self, websocket, expected_code, expected_reason=None):
        """
        Assert that the websocket is closed with the expected_code.
        """
        opcode, payload = websocket.recv_data()
        # ensure it's a close frame
        self.assertEqual(opcode, 8)
        code = struct.unpack('!H', payload[:2])[0]
        # ensure the close code is the one we expected
        self.assertEqual(code, expected_code)
        if expected_reason:
            # ensure the close reason is the one we expected
            self.assertEqual(payload[2:].decode(), expected_reason)


class BusCase:
    def _reset_bus(self):
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.env["bus.bus"].sudo().search([]).unlink()
