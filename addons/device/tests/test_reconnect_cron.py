import time
from datetime import timedelta
from unittest.mock import patch

import requests

from odoo import fields

from odoo.addons.device.tests.common import DeviceTransactionCase


class TestAutoReconnectCron(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Reconnect Cron Config")

    def _unreachable_devices(self, count):
        return self.env["device.device"].create(
            [
                {
                    "name": f"Unreachable {index}",
                    "identifier": f"CRON-UNREACH-{index}",
                    "config_id": self.config.id,
                    "comm_protocol": "http",
                    "endpoint": "10.255.255.1",
                    "connection_state": "error",
                }
                for index in range(count)
            ]
        )

    def test_the_cron_stops_at_its_time_budget(self):
        devices = self._unreachable_devices(20)
        model = self.env["device.device"]
        attempted = []

        def slow_connect(device):
            attempted.append(device.id)
            clock[0] += model._RECONNECT_BUDGET_SECONDS / 8
            raise TimeoutError("device unreachable")

        clock = [0.0]
        with (
            patch.object(type(devices), "action_connect", slow_connect),
            patch.object(time, "monotonic", lambda: clock[0]),
        ):
            model._cron_auto_reconnect()

        self.assertGreater(len(attempted), 0, "the cron attempted nothing at all")
        self.assertLess(
            len(attempted),
            len(devices),
            "the cron worked through every device regardless of elapsed time",
        )

    def test_a_failing_device_is_paced_by_its_connection_s_breaker(self):
        device = self._unreachable_devices(1)
        connection = device.sudo().connection_id
        connection.breaker_failure_threshold = 2

        def refuse(*_args, **_kwargs):
            raise requests.exceptions.ConnectionError("unreachable")

        with patch.object(requests.Session, "request", refuse):
            for _ in range(2):
                self.env["device.device"]._cron_auto_reconnect()
        self.assertTrue(device._connection_paused())

        attempted = []
        with patch.object(
            type(device), "action_connect", lambda dev: attempted.append(dev.id)
        ):
            self.env["device.device"]._cron_auto_reconnect()
        self.assertNotIn(device.id, attempted, "a paused connection sits the tick out")

    def test_a_pushing_device_is_never_redialled(self):
        device = self._unreachable_devices(1)
        device.link_mode = "push"
        attempted = []
        with patch.object(
            type(device), "action_connect", lambda dev: attempted.append(dev.id)
        ):
            self.env["device.device"]._cron_auto_reconnect()
        self.assertNotIn(device.id, attempted)
        self.assertFalse(device.sudo().connection_id)

    def test_the_connect_timeout_is_shorter_than_the_read_timeout(self):
        device = self._unreachable_devices(1)
        captured = {}

        def fake_request(*_args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            raise requests.exceptions.ConnectTimeout("unreachable")

        with patch.object(requests.Session, "request", fake_request):
            with self.assertRaises(requests.RequestException):
                device.http_read_data()

        connect_timeout, read_timeout = captured["timeout"]
        self.assertEqual(connect_timeout, self.config.service_id.timeout_connect)
        self.assertLess(connect_timeout, read_timeout)
        self.assertEqual(read_timeout, self.config.http_timeout)


class TestPollCron(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Poll Cron Config")

    def _connected_devices(self, count):
        return self.env["device.device"].create(
            [
                {
                    "name": f"Polled {index}",
                    "identifier": f"CRON-POLL-{index}",
                    "config_id": self.config.id,
                    "comm_protocol": "http",
                    "endpoint": "10.255.255.1",
                    "connection_state": "connected",
                    "date_last_data_received": fields.Datetime.now()
                    - timedelta(minutes=index),
                }
                for index in range(count)
            ]
        )

    def test_the_poll_cron_stops_at_its_time_budget(self):
        devices = self._connected_devices(20)
        model = self.env["device.device"]
        polled = []

        def slow_read(device):
            polled.append(device.id)
            clock[0] += model._POLL_BUDGET_SECONDS / 8
            return {}

        clock = [0.0]
        with (
            patch.object(type(devices), "action_read_data", slow_read),
            patch.object(time, "monotonic", lambda: clock[0]),
        ):
            model._cron_poll_devices()

        self.assertGreater(len(polled), 0, "the cron polled nothing at all")
        self.assertLess(
            len(polled),
            len(devices),
            "the cron worked through every device regardless of elapsed time",
        )

    def test_the_poll_cron_takes_the_least_recently_heard_from_first(self):
        devices = self._connected_devices(5)
        polled = []

        with patch.object(
            type(devices), "action_read_data", lambda device: polled.append(device.id)
        ):
            self.env["device.device"]._cron_poll_devices()

        oldest_first = devices.sorted(key=lambda d: d.date_last_data_received).ids
        self.assertEqual(
            [device_id for device_id in polled if device_id in oldest_first],
            oldest_first,
        )
