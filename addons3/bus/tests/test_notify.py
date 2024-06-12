# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import BaseCase

from ..models.bus import json_dump, get_notify_payloads, NOTIFY_PAYLOAD_MAX_LENGTH


class NotifyTests(BaseCase):

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
