from unittest.mock import patch

import requests

from odoo.exceptions import UserError

from odoo.addons.device.tests.common import (
    DeviceTransactionCase,
    InlineStateRetryMixin,
)


class _DeviceFixture(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["device.profile"].create({"name": "Regression Config"})

    def _make_device(self, **overrides):
        vals = {
            "name": "Regression Device",
            "identifier": "REG-DEFAULT",
            "config_id": self.config.id,
            "comm_protocol": "http",
            "endpoint": "10.0.0.1",
        }
        vals.update(overrides)
        return self.env["device.device"].create(vals)


class TestDeviceBusNotifications(_DeviceFixture):
    def test_bus_send_does_not_raise(self):
        device = self._make_device(identifier="REG-BUS")
        device._bus_send("device_status", {"connection_state": "connected"})

    def test_bus_channel_resolves_to_the_record(self):
        device = self._make_device(identifier="REG-BUS-CHANNEL")
        self.assertEqual(device._bus_channel(), device)


class TestDeviceConnectionFeedback(_DeviceFixture):
    def test_action_connect_raises_when_the_handler_returns_false(self):
        device = self._make_device(identifier="REG-CONNECT")
        with patch.object(type(device), "http_connect", return_value=False):
            with self.assertRaises(UserError):
                device.action_connect()

    def test_test_connection_reports_failure(self):
        device = self._make_device(identifier="REG-TEST-CONN")
        with patch.object(type(device), "http_connect", return_value=False):
            notification = device.action_test_connection()
        self.assertEqual(notification["params"]["type"], "danger")

    def test_test_connection_reports_success(self):
        device = self._make_device(identifier="REG-TEST-OK")
        with patch.object(type(device), "http_connect", return_value=True):
            notification = device.action_test_connection()
        self.assertEqual(notification["params"]["type"], "success")


class TestManagerCanUseAuthenticatedDevices(InlineStateRetryMixin, _DeviceFixture):
    # device.profile.auth_password and auth_token are groups="base.group_system".
    # http_read_data used to read them on the acting user's env, so a member of
    # this module's own manager group who is not a system admin could not use a
    # basic-auth or a token-auth device at all.

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Remote Manager No Sysadmin",
                "login": "regression_remote_manager_auth",
                "group_ids": [(6, 0, [cls.env.ref("device.group_device_manager").id])],
            }
        )

    def setUp(self):
        super().setUp()
        self.assertFalse(
            self.manager.has_group("base.group_system"),
            "fixture must not hold system rights",
        )
        self.captured = {}

        def fake_request(_session, **kwargs):
            self.captured.update(kwargs)
            raise requests.exceptions.ConnectTimeout("unreachable")

        patcher = patch.object(requests.Session, "request", fake_request)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _read_as_manager(self, device):
        with self.assertRaises(requests.RequestException):
            device.with_user(self.manager).http_read_data()

    def test_a_manager_reaches_the_network_on_a_basic_auth_profile(self):
        profile = self._create_device_profile(
            name="Regression Basic Profile",
            auth_type="basic",
            auth_username="device-user",
            auth_password="device-secret",
        )
        device = self._make_device(identifier="REG-AUTH-BASIC", config_id=profile.id)

        self._read_as_manager(device)

        self.assertEqual(self.captured["auth"], ("device-user", "device-secret"))

    def test_a_manager_reaches_the_network_on_a_token_profile(self):
        profile = self._create_device_profile(
            name="Regression Token Profile",
            auth_type="bearer",
            auth_token="device-token",
        )
        device = self._make_device(identifier="REG-AUTH-TOKEN", config_id=profile.id)

        self._read_as_manager(device)

        self.assertEqual(
            self.captured["headers"]["Authorization"], "Bearer device-token"
        )

    def test_test_connection_does_not_report_a_permission_error(self):
        profile = self._create_device_profile(
            name="Regression Basic Profile Feedback",
            auth_type="basic",
            auth_username="device-user",
            auth_password="device-secret",
        )
        device = self._make_device(identifier="REG-AUTH-FEEDBACK", config_id=profile.id)

        notification = device.with_user(self.manager).action_test_connection()

        self.assertEqual(notification["params"]["type"], "danger")
        self.assertNotIn("enough rights", notification["params"]["message"])
        self.assertNotIn("enough rights", device.connection_state_message or "")


class TestDeviceCreation(_DeviceFixture):
    def test_same_name_devices_coexist(self):
        first = self._make_device(name="Gate Reader", identifier="REG-NAME-A")
        second = self._make_device(name="Gate Reader", identifier="REG-NAME-B")
        self.assertNotEqual(first.credential_id, second.credential_id)

    def test_remote_manager_without_credential_rights_can_create(self):
        manager = self.env["res.users"].create(
            {
                "name": "Remote Manager",
                "login": "regression_remote_manager",
                "group_ids": [(6, 0, [self.env.ref("device.group_device_manager").id])],
            }
        )
        self.assertFalse(
            manager.has_group("credential.group_credential_user"),
            "fixture must not hold credential rights",
        )
        device = (
            self.env["device.device"]
            .with_user(manager)
            .create(
                {
                    "name": "Created By Manager",
                    "identifier": "REG-ACL",
                    "config_id": self.config.id,
                }
            )
        )
        self.assertTrue(device.credential_id)


class TestConnectionStateWrites(_DeviceFixture):
    def test_state_is_not_rewritten_when_unchanged(self):
        device = self._make_device(identifier="REG-STATE")
        device._set_connection_state("connected", "up")
        self.env.flush_all()
        before = device.write_date

        device._set_connection_state("connected", "up")
        self.env.flush_all()

        self.assertEqual(device.write_date, before)

    def test_state_changes_are_written(self):
        device = self._make_device(identifier="REG-STATE-CHANGE")
        device._set_connection_state("error", "boom")
        self.assertEqual(device.connection_state, "error")
        self.assertEqual(device.connection_state_message, "boom")

    def test_touch_last_seen_promotes_and_stamps(self):
        device = self._make_device(identifier="REG-TOUCH")
        device._set_connection_state("disconnected", "stale")

        device._touch_last_seen()

        self.assertEqual(device.connection_state, "connected")
        self.assertFalse(device.connection_state_message)
        self.assertTrue(device.date_last_data_received)
