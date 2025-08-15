# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import selectors
import threading

import odoo
from odoo.tests import TransactionCase

from ..models.bus import json_dump, get_notify_payloads, NOTIFY_PAYLOAD_MAX_LENGTH, ODOO_NOTIFY_FUNCTION


class NotifyTests(TransactionCase):

    def test_get_notify_payloads(self):
        """
        Asserts that the implementation of `get_notify_payloads`
        actually splits correctly large payloads
        """
        def check_payloads_size(payloads):
            for payload in payloads:
                self.assertLess(len(payload.encode()), NOTIFY_PAYLOAD_MAX_LENGTH)

        channel = ('dummy_db', 'dummy_model', 12345)
        channels = [channel]
        self.assertLess(len(json_dump(channels).encode()), NOTIFY_PAYLOAD_MAX_LENGTH)
        payloads = get_notify_payloads(channels)
        self.assertEqual(len(payloads), 1,
                         "The payload is less then the threshold, "
                         "there should be 1 payload only, as it shouldn't be split")
        channels = [channel] * 100
        self.assertLess(len(json_dump(channels).encode()), NOTIFY_PAYLOAD_MAX_LENGTH)
        payloads = get_notify_payloads(channels)
        self.assertEqual(len(payloads), 1,
                         "The payload is less then the threshold, "
                         "there should be 1 payload only, as it shouldn't be split")
        check_payloads_size(payloads)
        channels = [channel] * 1000
        self.assertGreaterEqual(len(json_dump(channels).encode()), NOTIFY_PAYLOAD_MAX_LENGTH)
        payloads = get_notify_payloads(channels)
        self.assertGreater(len(payloads), 1,
                           "Payload was larger than the threshold, it should've been split")
        check_payloads_size(payloads)

        fat_channel = tuple(item * 1000 for item in channel)
        channels = [fat_channel]
        self.assertEqual(len(channels), 1, "There should be only 1 channel")
        self.assertGreaterEqual(len(json_dump(channels).encode()), NOTIFY_PAYLOAD_MAX_LENGTH)
        payloads = get_notify_payloads(channels)
        self.assertEqual(len(payloads), 1,
                         "Payload was larger than the threshold, but shouldn't be split, "
                         "as it contains only 1 channel")
        with self.assertRaises(AssertionError):
            check_payloads_size(payloads)

    def test_postcommit(self):
        """Asserts all ``postcommit`` channels are fetched with a single listen."""
        if ODOO_NOTIFY_FUNCTION != 'pg_notify':
            return
        channels = []
        stop_event = threading.Event()
        selector_ready_event = threading.Event()

        def single_listen():
            nonlocal channels
            with odoo.sql_db.db_connect(
                "postgres"
            ).cursor() as cr, selectors.DefaultSelector() as sel:
                cr.execute("listen imbus")
                cr.commit()
                conn = cr._cnx
                sel.register(conn, selectors.EVENT_READ)
                selector_ready_event.set()
                while not stop_event.is_set():
                    if sel.select(timeout=5):
                        conn.poll()
                        if notify_channels := [
                            c
                            for c in json.loads(conn.notifies.pop().payload)
                            if c[0] == self.env.cr.dbname
                        ]:
                            channels = notify_channels
                            break

        thread = threading.Thread(target=single_listen)
        thread.start()
        selector_ready_event.wait(timeout=5)

        self.env["bus.bus"].search([]).unlink()
        self.env["bus.bus"]._sendone("channel 1", "test 1", {})
        self.env["bus.bus"]._sendone("channel 2", "test 2", {})
        self.env["bus.bus"]._sendone("channel 1", "test 3", {})
        self.assertEqual(self.env["bus.bus"].search_count([]), 0)
        self.assertEqual(channels, [])
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.assertEqual(self.env["bus.bus"].search_count([]), 3)
        self.assertEqual(channels, [])
        self.env.cr.postcommit.run()  # notify
        thread.join(timeout=5)
        stop_event.set()
        self.assertEqual(self.env["bus.bus"].search_count([]), 3)
        self.assertEqual(
            channels, [[self.env.cr.dbname, "channel 1"], [self.env.cr.dbname, "channel 2"]]
        )
