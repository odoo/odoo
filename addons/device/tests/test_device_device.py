import hashlib
import json
from datetime import timedelta
from unittest.mock import patch

from psycopg import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.device.models.device_device import TRANSPORT_VERBS
from odoo.addons.device.tests.common import (
    DeviceTransactionCase,
    InlineStateRetryMixin,
)


class TestRemoteDeviceBasic(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Test Config",
                "auth_type": "bearer",
                "auth_token": "test_token_123",
            },
        )

        cls.category = cls.env["device.kind"].create(
            {
                "name": "Test Category",
                "code": "TEST_CAT",
                "comm_protocol": "http",
            },
        )

    def test_create_device(self):
        device = self.env["device.device"].create(
            {
                "name": "Test Device",
                "identifier": "TEST-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": self.company.id,
            },
        )

        self.assertEqual(device.name, "Test Device")
        self.assertEqual(device.identifier, "TEST-001")
        self.assertEqual(device.comm_protocol, "http")
        self.assertEqual(device.connection_state, "disconnected")
        self.assertTrue(device.active)

    def test_create_device_auto_credential(self):
        device = self.env["device.device"].create(
            {
                "name": "Auto Cred Device",
                "identifier": "AUTO-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.101",
                "company_id": self.company.id,
            },
        )

        self.assertTrue(device.credential_id)
        self.assertIn("Token", device.credential_id.name)

    def test_credential_fingerprint_reverse_lookup(self):
        device = self.env["device.device"].create(
            {
                "name": "Token Lookup Device",
                "identifier": "TOKEN-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.150",
                "company_id": self.company.id,
            },
        )
        token = device.credential_id.credential_value
        self.assertTrue(token)
        expected = hashlib.sha256(token.encode()).hexdigest()
        self.assertEqual(device.credential_fingerprint, expected)

        found = self.env["device.device"]._find_by_inbound_token(token)
        self.assertIn(device, found)
        self.assertFalse(
            self.env["device.device"]._find_by_inbound_token("not-the-token")
        )
        self.assertFalse(self.env["device.device"]._find_by_inbound_token(""))

    def test_credential_fingerprint_tracks_rotation(self):
        device = self.env["device.device"].create(
            {
                "name": "Rotating Device",
                "identifier": "ROT-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.151",
                "company_id": self.company.id,
            },
        )
        old_fingerprint = device.credential_fingerprint
        device.credential_id.credential_value = "rotated-secret-value"
        device.invalidate_recordset(["credential_fingerprint"])
        self.assertNotEqual(device.credential_fingerprint, old_fingerprint)
        self.assertEqual(
            device.credential_fingerprint,
            hashlib.sha256(b"rotated-secret-value").hexdigest(),
        )
        self.assertIn(
            device,
            self.env["device.device"]._find_by_inbound_token("rotated-secret-value"),
        )

    def test_identifier_uniqueness_per_company(self):
        self.env["device.device"].create(
            {
                "name": "Device 1",
                "identifier": "UNIQUE-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": self.company.id,
            },
        )

        try:
            self.env["device.device"].create(
                {
                    "name": "Device 2",
                    "identifier": "UNIQUE-001",
                    "config_id": self.config.id,
                    "comm_protocol": "http",
                    "endpoint": "192.168.1.101",
                    "company_id": self.company.id,
                },
            )
        except IntegrityError, ValidationError:
            pass
        else:
            self.fail("Duplicate identifier per company should raise")

    def test_comm_protocol_selection(self):
        protocols = [
            code
            for code, _label in self.env["device.device"]
            ._fields["comm_protocol"]
            .get_description(self.env)["selection"]
        ]

        for i, protocol in enumerate(protocols):
            device = self.env["device.device"].create(
                {
                    "name": f"Protocol {protocol} Device",
                    "identifier": f"PROTO-{i:03d}",
                    "config_id": self.config.id,
                    "comm_protocol": protocol,
                    "endpoint": f"192.168.1.{100 + i}",
                    "company_id": self.company.id,
                },
            )
            self.assertEqual(device.comm_protocol, protocol)

    def test_connection_state_selection(self):
        device = self.env["device.device"].create(
            {
                "name": "State Test Device",
                "identifier": "STATE-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": self.company.id,
            },
        )

        for state in ["disconnected", "connected", "error"]:
            device.connection_state = state
            self.assertEqual(device.connection_state, state)


class TestRemoteDeviceEndpointDisplay(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Display Test Config",
            },
        )

    def _create_device(self, **kwargs):
        default_vals = {
            "name": "Display Test Device",
            "identifier": "DISP-001",
            "config_id": self.config.id,
            "company_id": self.company.id,
        }
        default_vals.update(kwargs)
        return self.env["device.device"].create(default_vals)

    def test_display_endpoint_http(self):
        device = self._create_device(
            comm_protocol="http",
            endpoint="api.example.com",
            port=8080,
            http_endpoint_path="/api/data",
        )

        self.assertEqual(
            device.display_endpoint, "http://api.example.com:8080/api/data"
        )

    def test_display_endpoint_https(self):
        device = self._create_device(
            identifier="DISP-002",
            comm_protocol="https",
            endpoint="secure.example.com",
        )

        self.assertIn("https://", device.display_endpoint)

    def test_http_falls_back_to_the_profile_host_and_port(self):
        self.config.write({"endpoint_url": "http://192.168.1.10:8080"})
        device = self._create_device(
            identifier="DISP-FALLBACK",
            comm_protocol="http",
            http_endpoint_path="/api/data",
        )

        self.assertEqual(device._get_effective_endpoint(), "192.168.1.10")
        self.assertEqual(device.display_endpoint, "http://192.168.1.10:8080/api/data")

    def test_display_endpoint_is_empty_when_no_host_resolves(self):
        device = self._create_device(identifier="DISP-NOHOST", comm_protocol="http")

        self.assertFalse(
            device.display_endpoint,
            "a device with no host anywhere must not render a host of 'False'",
        )

    def test_the_poll_cron_sees_a_device_that_only_has_a_profile_host(self):
        self.config.write({"endpoint_url": "http://192.168.1.10"})
        device = self._create_device(
            identifier="DISP-CRON",
            comm_protocol="http",
            connection_state="connected",
        )

        self.assertEqual(device.link_mode, "pull")
        eligible = self.env["device.device"].search(
            [
                ("connection_state", "=", "connected"),
                ("link_mode", "=", "pull"),
                ("active", "=", True),
                ("is_demo", "=", False),
            ]
        )
        self.assertIn(device, eligible)


class TestDeviceCategoryPresentation(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Presentation Config")

    def _device_on(self, category):
        return self._create_device_device(
            config=self.config,
            identifier=f"PRESENT-{category.code}",
            device_category_id=category.id,
        )

    def test_a_category_decides_its_own_icon_and_colour(self):
        category = self.env["device.kind"].create(
            {
                "name": "Owned Look",
                "code": "gps_tracker",
                "icon": "fa-id-card",
                "color": 9,
            },
        )

        device = self._device_on(category)

        self.assertEqual(device.category_icon, "fa-id-card")
        self.assertEqual(device.category_color, 9)

    def test_no_shipped_category_renders_something_other_than_what_it_stores(self):
        for category in self.env["device.kind"].search([]):
            with self.subTest(code=category.code):
                device = self._device_on(category)
                self.assertEqual(device.category_icon, category.icon or "fa-microchip")
                self.assertEqual(device.category_color, category.color or 0)


class TestRemoteDeviceLogComputation(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Log Test Config",
            },
        )

        cls.device = cls.env["device.device"].create(
            {
                "name": "Log Test Device",
                "identifier": "LOG-001",
                "config_id": cls.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": cls.company.id,
            },
        )

    def test_log_count_empty(self):
        self.assertEqual(self.device.log_count, 0)

    def test_log_count_with_data(self):
        for i in range(5):
            self.env["device.data.log"].create(
                {
                    "device_id": self.device.id,
                    "data_type": "json",
                    "value_json": {"temp": 20 + i},
                },
            )

        self.device._compute_log_count()
        self.assertEqual(self.device.log_count, 5)

    def test_log_last_id_tracks_the_latest_stored_point(self):
        first = self.device._store_data_point({"temp": 20}, source_topic="test")
        self.device.invalidate_recordset()
        self.assertEqual(self.device.log_last_id, first)

        second = self.device._store_data_point({"temp": 25}, source_topic="test")
        self.device.invalidate_recordset()
        self.assertEqual(self.device.log_last_id, second)


class TestRemoteDeviceDataStorage(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Storage Test Config",
            },
        )

        cls.device = cls.env["device.device"].create(
            {
                "name": "Storage Test Device",
                "identifier": "STORE-001",
                "config_id": cls.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": cls.company.id,
            },
        )

    def test_store_json_data(self):
        data = {"temperature": 25.5, "humidity": 60, "status": "online"}

        point = self.device._store_data_point(
            data,
            source_topic="http://192.168.1.100/api/data",
            raw_payload=json.dumps(data),
        )

        self.assertEqual(point.device_id, self.device)
        self.assertEqual(point.data_type, "json")
        self.assertEqual(point.quality, "good")
        self.assertIsNotNone(self.device.date_last_data_received)

    def test_store_data_updates_last_received(self):
        initial_time = self.device.date_last_data_received

        self.device._store_data_point(
            {"test": True},
            source_topic="test",
        )

        self.assertNotEqual(self.device.date_last_data_received, initial_time)


class TestDegradedDataPointWrite(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Degraded Config")
        cls.device = cls._create_device_device(
            config=cls.config, identifier="DEGRADED-001"
        )

    def test_a_database_error_on_the_json_write_still_stores_the_payload(self):
        log_model = type(self.env["device.data.log"])
        original_create = log_model.create
        attempts = []

        def failing_first_create(model, vals_list):
            attempts.append(1)
            if len(attempts) == 1:
                model.env.cr.execute("SELECT 1 / 0")
            return original_create(model, vals_list)

        with patch.object(log_model, "create", failing_first_create):
            point = self.device._store_data_point(
                {"temperature": 21}, source_topic="degraded", raw_payload="{}"
            )

        self.assertEqual(len(attempts), 2, "the fallback create never ran")
        self.assertEqual(point.data_type, "text")
        self.assertEqual(point.quality, "bad")
        self.assertIn("temperature", point.value_text)


class TestRemoteDeviceDemoMode(InlineStateRetryMixin, DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Demo Test Config",
            },
        )

    def test_demo_device_flag(self):
        device = self.env["device.device"].create(
            {
                "name": "Demo Device",
                "identifier": "DEMO-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": self.company.id,
                "is_demo": True,
            },
        )

        self.assertTrue(device.is_demo)

    def test_demo_generate_http_data(self):
        device = self.env["device.device"].create(
            {
                "name": "Demo HTTP Device",
                "identifier": "DEMO-HTTP-001",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": self.company.id,
                "is_demo": True,
            },
        )

        data = device._demo_generate_http_data()

        self.assertTrue(data["demo"])
        self.assertIn("temperature", data)
        self.assertIn("humidity", data)
        self.assertEqual(device.connection_state, "connected")


class TestRemoteDeviceTokenGeneration(DeviceTransactionCase):
    def test_generate_api_token(self):
        token = self.env["device.device"]._generate_api_token()

        self.assertEqual(len(token), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in token))

    def test_generate_api_token_unique(self):
        tokens = [self.env["device.device"]._generate_api_token() for _ in range(100)]

        self.assertEqual(len(tokens), len(set(tokens)))


class TestRemoteDeviceCronCheckHealth(InlineStateRetryMixin, DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.config = cls.env["device.profile"].create(
            {
                "name": "Health Test Config",
                "auth_type": "bearer",
                "auth_token": "health_token",
            },
        )
        cls.category_default = cls.env["device.kind"].create(
            {
                "name": "Health Default Category",
                "code": "HEALTH_DEFAULT",
                "comm_protocol": "http",
            },
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "device.disconnect_timeout_default", "600"
        )

    def _make_device(self, **overrides):
        vals = {
            "name": overrides.pop("name", "Health Device"),
            "identifier": overrides.pop("identifier", "HEALTH-001"),
            "config_id": self.config.id,
            "comm_protocol": "http",
            "endpoint": "10.0.0.1",
            "company_id": self.company.id,
            "device_category_id": self.category_default.id,
        }
        vals.update(overrides)
        return self.env["device.device"].create(vals)

    def test_promotes_disconnected_with_fresh_data(self):
        device = self._make_device(identifier="PROMOTE-FRESH")
        device.write(
            {
                "connection_state": "disconnected",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=30),
            },
        )

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "connected")
        self.assertFalse(device.connection_state_message)

    def test_promotes_error_state_with_fresh_data(self):
        device = self._make_device(identifier="PROMOTE-FROM-ERROR")
        device.write(
            {
                "connection_state": "error",
                "connection_state_message": "old error",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=10),
            },
        )

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "connected")
        self.assertFalse(device.connection_state_message)

    def test_demotes_connected_when_stale(self):
        device = self._make_device(identifier="DEMOTE-STALE")
        device.write(
            {
                "connection_state": "connected",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=1200),
            },
        )

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "disconnected")

    def test_keeps_disconnected_when_no_data_ever_received(self):
        device = self._make_device(identifier="NEVER-DATA")

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "disconnected")
        self.assertFalse(device.date_last_data_received)

    def test_per_category_timeout_override(self):
        long_category = self.env["device.kind"].create(
            {
                "name": "Long Timeout",
                "code": "LONG_TIMEOUT",
                "comm_protocol": "http",
                "disconnect_timeout_seconds": 3600,
            },
        )
        device = self._make_device(
            identifier="LONG-TIMEOUT",
            device_category_id=long_category.id,
        )
        device.write(
            {
                "connection_state": "connected",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=1800),
            },
        )

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "connected")

    def test_persistent_protocols_stay_on_error_semantics(self):
        device = self._make_device(
            identifier="SOCKET-STALE",
            comm_protocol="https",
        )
        device.write(
            {
                "link_mode": "stream",
                "connection_state": "connected",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=1200),
            },
        )

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "error")

    def test_persistent_protocols_not_promoted_by_cron(self):
        device = self._make_device(
            identifier="SOCKET-DISC",
            comm_protocol="https",
        )
        device.write(
            {
                "link_mode": "stream",
                "connection_state": "disconnected",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=10),
            },
        )

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "disconnected")

    def test_archived_devices_skipped(self):
        device = self._make_device(identifier="ARCHIVED")
        device.write(
            {
                "connection_state": "connected",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=1200),
                "active": False,
            },
        )

        self.env["device.device"]._cron_check_health()

        self.assertEqual(device.connection_state, "connected")

    def test_the_quiet_alert_names_the_state_it_was_given(self):
        device = self._make_device(identifier="QUIET-ALERT")
        self.config.alert_on_disconnect = True
        device.write(
            {
                "connection_state": "connected",
                "date_last_data_received": fields.Datetime.now()
                - timedelta(seconds=1200),
            },
        )

        # The cron writes the demotion on a cursor of its own, so this
        # transaction can still read "connected" here. The message must name the
        # state the cron decided, never the one the record still shows.
        device._notify_devices_went_quiet("disconnected")

        message = self.env["mail.message"].search(
            [("model", "=", "device.device"), ("res_id", "=", device.id)],
            order="id desc",
            limit=1,
        )
        self.assertIn("Status is now disconnected", message.body)
        self.assertNotIn("Status is now connected", message.body)

    def test_the_quiet_alert_distinguishes_a_stale_socket_from_a_quiet_poll(self):
        polled = self._make_device(identifier="QUIET-POLLED")
        socket = self._make_device(identifier="QUIET-SOCKET", comm_protocol="https")
        socket.link_mode = "stream"
        self.config.alert_on_disconnect = True
        for device in (polled, socket):
            device.write(
                {
                    "connection_state": "connected",
                    "date_last_data_received": fields.Datetime.now()
                    - timedelta(seconds=1200),
                },
            )

        self.env["device.device"]._cron_check_health()

        for device, expected in ((polled, "disconnected"), (socket, "error")):
            with self.subTest(device=device.identifier):
                self.assertEqual(device.connection_state, expected)
                message = self.env["mail.message"].search(
                    [("model", "=", "device.device"), ("res_id", "=", device.id)],
                    order="id desc",
                    limit=1,
                )
                self.assertIn(f"Status is now {expected}", message.body)


class TestRemoteDeviceRegisterHook(InlineStateRetryMixin, DeviceTransactionCase):
    """The startup reset belongs to the base, whatever transport is installed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["device.profile"].create(
            {
                "name": "Register Hook Config",
                "auth_type": "none",
            },
        )
        cls.device = cls.env["device.device"].create(
            {
                "name": "Register Hook Device",
                "identifier": "REGISTER-HOOK-001",
                "config_id": cls.config.id,
                "comm_protocol": "https",
                "company_id": cls.env.ref("base.main_company").id,
            },
        )

    def setUp(self):
        super().setUp()
        self.device.write(
            {
                "connection_state": "connected",
                "connection_state_message": "Connected successfully",
            },
        )

    def _run_register_hook(self, protocols=("https",), streamed=()):
        # https stands in for a persistent transport. This module ships none,
        # and what the reset turns on is holding a connection open in this
        # process, not which protocol holds it.
        model_cls = type(self.device)
        with (
            patch.object(
                model_cls, "_persistent_protocols", return_value=list(protocols)
            ),
            patch.object(model_cls, "_streamed_protocols", return_value=list(streamed)),
        ):
            self.env["device.device"]._register_hook()

    def test_reset_runs_for_a_persistent_protocol(self):
        self._run_register_hook()

        self.assertEqual(self.device.connection_state, "disconnected")
        self.assertEqual(
            self.device.connection_state_message, "Reset on server restart"
        )

    def test_reset_leaves_a_streamed_protocol_alone(self):
        self._run_register_hook(streamed=("https",))

        self.assertEqual(
            self.device.connection_state,
            "connected",
            "the stream worker holds that connection, and the row says its state",
        )
        self.assertEqual(self.device.connection_state_message, "Connected successfully")

    def test_reset_touches_nothing_when_no_persistent_transport_is_installed(self):
        self._run_register_hook(protocols=())

        self.assertEqual(self.device.connection_state, "connected")
        self.assertEqual(self.device.connection_state_message, "Connected successfully")


@tagged("post_install", "-at_install")
class TestTransportContract(DeviceTransactionCase):
    """Every protocol on offer must supply every verb the dispatcher calls."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["device.profile"].create({"name": "Contract Config"})

    def _protocols(self):
        return [
            code
            for code, _label in self.env["device.device"]
            ._fields["comm_protocol"]
            .get_description(self.env)["selection"]
        ]

    def test_every_offered_protocol_implements_every_transport_verb(self):
        missing = {}
        for index, protocol in enumerate(self._protocols()):
            device = self.env["device.device"].create(
                {
                    "name": f"Contract {protocol}",
                    "identifier": f"CONTRACT-{index:03d}",
                    "config_id": self.config.id,
                    "comm_protocol": protocol,
                    "endpoint": "10.0.0.1",
                },
            )
            absent = [
                verb
                for verb in TRANSPORT_VERBS
                if device._transport_method(verb) is None
            ]
            if absent:
                missing[protocol] = absent
        self.assertFalse(
            missing,
            "comm_protocol offers a value whose transport is not installed. A "
            "protocol module adds its value and its verbs together: "
            f"{missing}",
        )

    def test_an_override_of_a_shared_verb_reaches_every_protocol_that_uses_it(self):
        device = self.env["device.device"].create(
            {
                "name": "Contract https override",
                "identifier": "CONTRACT-HTTPS-OVERRIDE",
                "config_id": self.config.id,
                "comm_protocol": "https",
                "endpoint": "10.0.0.1",
            },
        )
        model_cls = type(device)

        with patch.object(
            model_cls, "http_read_data", return_value={"overridden": True}
        ):
            self.assertEqual(
                device._transport_method("read_data")(),
                {"overridden": True},
                "https delegates to http by name, so an override must reach it",
            )

    def test_a_protocol_is_polled_or_persistent_but_not_both(self):
        device_model = self.env["device.device"]
        polled_list = device_model._polled_protocols()
        persistent_list = device_model._persistent_protocols()
        polled = set(polled_list)
        persistent = set(persistent_list)
        self.assertEqual(
            len(polled_list),
            len(polled),
            "a protocol declared itself polled twice -- one module is adding a "
            f"value the module below it already declares: {polled_list}",
        )
        self.assertEqual(
            len(persistent_list),
            len(persistent),
            "a protocol declared itself persistent twice -- one module is adding "
            f"a value the module below it already declares: {persistent_list}",
        )
        self.assertFalse(polled & persistent)
        self.assertEqual(
            polled | persistent,
            set(self._protocols()),
            "every offered protocol must declare whether Odoo polls it or it "
            "holds a connection open -- the health and reconnect crons ask",
        )


@tagged("post_install", "-at_install")
class TestDeviceKindContract(DeviceTransactionCase):
    """A device is a kind because a module declares it, not by field shape."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["device.profile"].create({"name": "Kind Config"})

    def _device(self, category=None, **overrides):
        vals = {
            "name": "Kind Device",
            "identifier": "KIND-001",
            "config_id": self.config.id,
            "comm_protocol": "http",
            "endpoint": "10.0.0.1",
        }
        if category is not None:
            vals["device_category_id"] = category.id
        vals.update(overrides)
        return self.env["device.device"].create(vals)

    def test_an_undeclared_kind_matches_nothing(self):
        device = self._device()
        self.assertFalse(device._is_device_kind("no_such_kind"))

    def test_a_kind_is_declared_by_category_not_inferred_from_a_field(self):
        model = self.env["device.device"]
        for kind in ("gps", "access", "counter", "dav"):
            codes = model._device_kind_categories(kind)
            if not codes:
                continue
            with self.subTest(kind=kind):
                self.assertEqual(
                    len(codes),
                    len(set(codes)),
                    f"two modules declared the same category for kind {kind}",
                )
                found = self.env["device.kind"].search([("code", "in", codes)])
                self.assertEqual(
                    set(found.mapped("code")),
                    set(codes),
                    f"kind {kind} names a category code no seed record uses -- "
                    "the classification silently matches nothing",
                )
