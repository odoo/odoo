# Part of Odoo. See LICENSE file for full copyright and licensing details.

import struct
from threading import Event
import unittest
from unittest.mock import patch

try:
    import websocket
except ImportError:
    websocket = None

import odoo.tools
from odoo.tests import HOST, HttpCase
from ..websocket import CloseCode, WebsocketConnectionHandler


class WebsocketCase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if websocket is None:
            cls._logger.warning("websocket-client module is not installed")
            raise unittest.SkipTest("websocket-client module is not installed")
        cls._WEBSOCKET_URL = f"ws://{HOST}:{odoo.tools.config['http_port']}/websocket"
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

    def websocket_connect(self, *args, **kwargs):
        """
        Connect a websocket. If no cookie is given, the connection is
        opened with a default session. The created websocket is closed
        at the end of the test.
        """
        if 'cookie' not in kwargs:
            self.session = self.authenticate(None, None)
            kwargs['cookie'] = f'session_id={self.session.sid}'
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 5
        ws = websocket.create_connection(
            type(self)._WEBSOCKET_URL, *args, **kwargs
        )
        self._websockets.add(ws)
        return ws

    def wait_remaining_websocket_connections(self):
        """ Wait for the websocket connections to terminate. """
        for event in self._websocket_events:
            event.wait(5)

    def assert_close_with_code(self, websocket, expected_code):
        """
        Assert that the websocket is closed with the expected_code.
        """
        opcode, payload = websocket.recv_data()
        # ensure it's a close frame
        self.assertEqual(opcode, 8)
        code = struct.unpack('!H', payload[:2])[0]
        # ensure the close code is the one we expected
        self.assertEqual(code, expected_code)
