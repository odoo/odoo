from unittest.mock import patch

import requests

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.device.tests.common import DeviceTransactionCase


@tagged("post_install", "-at_install")
class TestProfileIsAService(DeviceTransactionCase):
    def test_a_profile_carries_one_service_from_its_creation(self):
        profile = self._create_device_profile(
            name="Teltonika FMB920",
            auth_type="bearer",
            auth_token="t0ken",
            endpoint_url="https://gateway.example",
            http_timeout=12,
        )
        service = profile.service_id
        self.assertTrue(service)
        self.assertEqual(service.code, f"device_profile_{profile.id}")
        self.assertEqual(service.name, "Device profile: Teltonika FMB920")
        self.assertEqual(service.category, "device")
        self.assertTrue(service.per_record_connections)
        self.assertEqual(
            (service.auth_type, service.endpoint_url, service.timeout_read),
            ("bearer", "https://gateway.example", 12),
        )
        self.assertEqual(profile.sudo().credential_id.endpoint_id, service)
        self.assertEqual(profile.auth_token, "t0ken")

    def test_the_profile_edits_its_service(self):
        profile = self._create_device_profile(name="Editable")
        profile.write({"name": "Edited", "auth_type": "basic", "http_timeout": 7})
        self.assertEqual(profile.service_id.name, "Device profile: Edited")
        self.assertEqual(profile.service_id.auth_type, "basic")
        self.assertEqual(profile.service_id.timeout_read, 7)

    def test_a_shared_secret_binds_to_the_profile_s_service(self):
        profile = self._create_device_profile(name="Shared")
        credential = (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": "shared login",
                    "category_id": self.env.ref(
                        "credential.credential_category_basic_auth"
                    ).id,
                    "username": "gw",
                    "password": "pw",
                }
            )
        )
        profile.sudo().credential_id = credential
        self.assertEqual(credential.endpoint_id, profile.service_id)
        self.assertEqual(profile.sudo().auth_username, "gw")

    def test_a_plain_http_default_address_stays_on_a_private_network(self):
        profile = self._create_device_profile(name="LAN gateway")
        profile.endpoint_url = "http://192.168.1.10:8080"
        with self.assertRaises(ValidationError):
            profile.endpoint_url = "http://gateway.example"

    def test_deleting_the_profile_deletes_its_service(self):
        profile = self._create_device_profile(name="Gone")
        service = profile.service_id
        profile.unlink()
        self.assertFalse(service.exists())


@tagged("post_install", "-at_install")
class TestDeviceDialsThroughItsConnection(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.profile = cls._create_device_profile(
            name="Dialled", auth_type="basic", auth_username="u", auth_password="p"
        )

    def test_a_polled_device_with_an_address_gets_its_own_connection(self):
        device = self._create_device_device(
            config=self.profile, identifier="DIAL-1", endpoint="10.0.0.7", port=8081
        )
        connection = device.sudo().connection_id
        self.assertTrue(connection)
        self.assertEqual(connection.service_id, self.profile.service_id)
        self.assertEqual(connection.credential_id, self.profile.sudo().credential_id)
        self.assertEqual(connection.base_url, "http://10.0.0.7:8081")
        self.assertEqual(
            (connection.res_model, connection.res_id), (device._name, device.id)
        )

    def test_a_device_without_an_address_dials_the_profile_s_default(self):
        self.profile.endpoint_url = "http://10.0.0.1"
        device = self._create_device_device(
            config=self.profile, identifier="DIAL-DEFAULT", endpoint=False
        )
        connection = device.sudo().connection_id
        self.assertTrue(connection)
        self.assertFalse(connection.base_url)
        self.assertEqual(connection._base_url(), "http://10.0.0.1")

    def test_a_device_nobody_dials_has_no_connection(self):
        pushing = self._create_device_device(
            config=self._create_device_profile(name="No address"),
            identifier="DIAL-NONE",
            endpoint=False,
        )
        self.assertFalse(pushing.sudo().connection_id)

    def test_the_device_s_own_secret_wins_over_the_profile_s(self):
        own = (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": "own login",
                    "category_id": self.env.ref(
                        "credential.credential_category_basic_auth"
                    ).id,
                    "username": "me",
                    "password": "mine",
                }
            )
        )
        device = self._create_device_device(config=self.profile, identifier="DIAL-OWN")
        device.sudo().dial_credential_id = own
        self.assertEqual(device.sudo().connection_id.credential_id, own)

    def test_a_changed_address_moves_the_connection(self):
        device = self._create_device_device(config=self.profile, identifier="DIAL-MOVE")
        connection = device.sudo().connection_id
        device.write({"endpoint": "10.0.0.9", "port": 9000})
        self.assertEqual(device.sudo().connection_id, connection)
        self.assertEqual(connection.base_url, "http://10.0.0.9:9000")
        device.comm_protocol = "https"
        self.assertEqual(connection.base_url, "https://10.0.0.9:9000")

    def test_a_read_goes_through_the_connection_with_its_login(self):
        device = self._create_device_device(
            config=self.profile, identifier="DIAL-READ", http_endpoint_path="api/data"
        )
        captured = {}

        def fake_request(_session, method, url, **kwargs):
            captured.update(method=method, url=url, auth=kwargs.get("auth"))
            response = requests.Response()
            response.status_code = 200
            response.headers["content-type"] = "application/json"
            response._content = b'{"t": 21}'
            response.url = url
            return response

        with patch.object(requests.Session, "request", fake_request):
            data = device.http_read_data()

        self.assertEqual(data, {"t": 21})
        self.assertEqual(captured["url"], "http://10.0.0.1/api/data")
        self.assertEqual(captured["auth"], ("u", "p"))
        self.env.cr.precommit.run()
        connection = device.sudo().connection_id
        connection.invalidate_recordset()
        self.assertEqual(connection.circuit_state, "closed")

    def test_failures_pause_the_device_s_connection_alone(self):
        device = self._create_device_device(config=self.profile, identifier="DIAL-FAIL")
        other = self._create_device_device(
            config=self.profile, identifier="DIAL-OK", endpoint="10.0.0.2"
        )
        connection = device.sudo().connection_id
        connection.breaker_failure_threshold = 2

        def refuse(*_args, **_kwargs):
            raise requests.exceptions.ConnectionError("refused")

        with patch.object(requests.Session, "request", refuse):
            for _ in range(2):
                with self.assertRaises(requests.RequestException):
                    device.http_read_data()

        self.env.cr.precommit.run()
        connection.invalidate_recordset()
        self.assertEqual(connection.circuit_state, "open")
        self.assertEqual(other.sudo().connection_id.circuit_state, "closed")

    def test_deleting_the_device_deletes_its_connection(self):
        device = self._create_device_device(config=self.profile, identifier="DIAL-DEL")
        connection = device.sudo().connection_id
        device.unlink()
        self.assertFalse(connection.exists())


@tagged("post_install", "-at_install")
class TestLinkMode(DeviceTransactionCase):
    def test_the_mode_follows_the_protocol_and_the_address(self):
        profile = self._create_device_profile(name="Modes")
        dialled = self._create_device_device(config=profile, identifier="MODE-PULL")
        pushing = self._create_device_device(
            config=profile, identifier="MODE-PUSH", endpoint=False
        )
        self.assertEqual((dialled.link_mode, pushing.link_mode), ("pull", "push"))
        profile.endpoint_url = "http://10.0.0.1"
        self.assertEqual(pushing.link_mode, "pull")

    def test_a_device_set_to_push_keeps_no_connection_and_is_not_polled(self):
        device = self._create_device_device(
            config=self._create_device_profile(name="Phone"),
            identifier="MODE-HAND",
            connection_state="connected",
        )
        self.assertTrue(device.sudo().connection_id)
        device.link_mode = "push"
        self.assertFalse(device.sudo().connection_id)
        polled = []
        with patch.object(
            type(device), "action_read_data", lambda dev: polled.append(dev.id)
        ):
            self.env["device.device"]._cron_poll_devices()
        self.assertNotIn(device.id, polled)

    def test_the_kind_s_word_wins_over_the_address(self):
        phones = self.env["device.kind"].create(
            {"name": "Phones", "code": "test_phones", "link_mode": "push"}
        )
        device = self._create_device_device(
            config=self._create_device_profile(name="Phone profile"),
            identifier="MODE-KIND",
            device_category_id=phones.id,
        )
        self.assertEqual(device.link_mode, "push")
        self.assertFalse(device.sudo().connection_id)
        phones.link_mode = "pull"
        self.assertEqual(device.link_mode, "pull")
        self.assertTrue(device.sudo().connection_id)
