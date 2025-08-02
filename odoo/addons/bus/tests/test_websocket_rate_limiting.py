# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import time

try:
    from websocket._exceptions import WebSocketProtocolException
    from websocket._abnf import VALID_CLOSE_STATUS
except ImportError:
    pass

from odoo.tests import common
from .common import WebsocketCase
from ..websocket import CloseCode, Websocket

@common.tagged('post_install', '-at_install')
class TestWebsocketRateLimiting(WebsocketCase):
    def test_rate_limiting_base_ok(self):
        ws = self.websocket_connect()

        # slepeing after initial ping frame
        time.sleep(Websocket.RL_DELAY)

        for _ in range(Websocket.RL_BURST + 1):
            ws.send(json.dumps({'event_name': 'test_rate_limiting'}))
            time.sleep(Websocket.RL_DELAY)

    def test_rate_limiting_base_ko(self):
        def check_base_ko():
            for _ in range(Websocket.RL_BURST + 1):
                ws.send(json.dumps({'event_name': 'test_rate_limiting'}))
            self.assert_close_with_code(ws, CloseCode.TRY_LATER)

        ws = self.websocket_connect()

        if 1013 not in VALID_CLOSE_STATUS:
            # Websocket client's close codes are not up to date. Indeed, the
            # 1013 close code results in a protocol exception while it is a
            # valid, registered close code ("TRY LATER") :
            # https://www.iana.org/assignments/websocket/websocket.xhtml
            with self.assertRaises(WebSocketProtocolException) as cm:
                check_base_ko()
            self.assertEqual(str(cm.exception), 'Invalid close opcode.')
        else:
            check_base_ko()

    def test_rate_limiting_opening_burst(self):
        ws = self.websocket_connect()

        # slepeing after initial ping frame
        time.sleep(Websocket.RL_DELAY)

        # burst is allowed
        for _ in range(Websocket.RL_BURST // 2):
            ws.send(json.dumps({"event_name": "test_rate_limiting"}))

        # as long as the rate is respected afterwards
        for _ in range(Websocket.RL_BURST):
            time.sleep(Websocket.RL_DELAY * 2)
            ws.send(json.dumps({"event_name": "test_rate_limiting"}))

    def test_rate_limiting_start_ok_end_ko(self):
        def check_end_ko():
            # those requests are illicit and should not be accepted.
            for _ in range(Websocket.RL_BURST * 2):
                ws.send(json.dumps({'event_name': 'test_rate_limiting'}))
            self.assert_close_with_code(ws, CloseCode.TRY_LATER)

        ws = self.websocket_connect()

        # first requests are legit and should be accepted
        for _ in range(Websocket.RL_BURST + 1):
            ws.send(json.dumps({'event_name': 'test_rate_limiting'}))
            time.sleep(Websocket.RL_DELAY)

        if 1013 not in VALID_CLOSE_STATUS:
            # Websocket client's close codes are not up to date. Indeed, the
            # 1013 close code results in a protocol exception while it is a
            # valid, registered close code ("TRY LATER") :
            # https://www.iana.org/assignments/websocket/websocket.xhtml
            with self.assertRaises(WebSocketProtocolException) as cm:
                check_end_ko()
            self.assertEqual(str(cm.exception), 'Invalid close opcode.')
        else:
            check_end_ko()
