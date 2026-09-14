from itertools import count
from unittest.mock import MagicMock, patch

from requests.auth import HTTPDigestAuth

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.integration.tools import CommError, get_api_client
from odoo.addons.integration.tools.connection_migration import (
    connect_bound_credentials,
)


def _ok_response():
    response = MagicMock()
    response.status_code = 200
    response.ok = True
    response.headers = {"Content-Type": "application/json"}
    response.content = b"{}"
    response.text = "{}"
    response.json.return_value = {}
    return response


@tagged("post_install", "-at_install", "integration")
class TestIntegrationConnection(TransactionCase):
    _names = count()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Connection = cls.env["integration.connection"]
        cls.service = cls.env["integration.service"].create(
            {
                "name": "Connection probe",
                "code": "connection_probe",
                "endpoint_url": "https://live.example.com",
                "endpoint_url_test": "https://sandbox.example.com",
                "auth_type": "bearer",
                "environment": "production",
            }
        )
        cls.other_service = cls.env["integration.service"].create(
            {
                "name": "Other probe",
                "code": "other_connection_probe",
                "endpoint_url": "https://other.example.com",
                "auth_type": "bearer",
                "environment": "production",
            }
        )
        cls.category = cls.env.ref("credential.credential_category_bearer_token")

    def _credential(self, **overrides):
        return self.env["credential.credential"].create(
            {
                "name": f"Probe token {next(self._names)}",
                "category_id": self.category.id,
                "company_id": self.env.company.id,
                "environment": "production",
                "bearer_token": "token",
                **overrides,
            }
        )

    def _synced(self, credential):
        return self.Connection.with_context(active_test=False).search(
            [("credential_id", "=", credential.id)]
        )

    def test_binding_a_credential_creates_its_connection(self):
        credential = self._credential(endpoint_id=self.service.id, sequence=7)

        connection = self._synced(credential)

        self.assertEqual(len(connection), 1)
        self.assertTrue(connection.synced_from_credential)
        self.assertEqual(connection.service_id, self.service)
        self.assertEqual(connection.company_id, self.env.company)
        self.assertEqual(connection.environment, "production")
        self.assertEqual(connection.sequence, 7)

    def test_rebinding_moves_the_connection_and_unbinding_removes_it(self):
        credential = self._credential(endpoint_id=self.service.id)

        credential.endpoint_id = self.other_service
        self.assertEqual(self._synced(credential).service_id, self.other_service)

        credential.endpoint_id = False
        self.assertFalse(self._synced(credential))

    def test_archiving_the_credential_archives_its_connection(self):
        credential = self._credential(endpoint_id=self.service.id)

        credential.active = False

        self.assertFalse(self._synced(credential).active)
        self.assertFalse(self.Connection._resolve(self.service))

    def test_a_connection_in_another_environment_does_not_resolve(self):
        self._credential(endpoint_id=self.service.id, environment="test")

        self.assertFalse(self.Connection._resolve(self.service))
        self.assertTrue(self.Connection._resolve(self.service, environment="test"))

    def test_the_company_connection_wins_over_the_all_companies_one(self):
        shared = self._credential(endpoint_id=self.service.id, company_id=False)
        own = self._credential(endpoint_id=self.service.id)

        self.assertEqual(self.Connection._resolve(self.service).credential_id, own)
        own.active = False
        self.assertEqual(self.Connection._resolve(self.service).credential_id, shared)

    def test_a_personal_connection_wins_only_where_the_service_allows_it(self):
        company = self._credential(endpoint_id=self.service.id)
        personal = self._credential(
            endpoint_id=self.service.id, owner_user_id=self.env.uid
        )

        self.assertEqual(self.Connection._resolve(self.service).credential_id, company)
        self.service.allow_user_credentials = True
        self.assertEqual(self.Connection._resolve(self.service).credential_id, personal)

    def test_two_active_connections_on_one_scope_are_refused(self):
        self._credential(endpoint_id=self.service.id)

        with self.assertRaises(ValidationError):
            self.Connection.create(
                {
                    "service_id": self.service.id,
                    "credential_id": self._credential().id,
                    "company_id": self.env.company.id,
                    "environment": "production",
                }
            )

    def test_a_credential_bound_to_one_service_cannot_connect_another(self):
        credential = self._credential(endpoint_id=self.other_service.id)

        with self.assertRaises(ValidationError):
            self.Connection.create(
                {
                    "service_id": self.service.id,
                    "credential_id": credential.id,
                    "environment": "production",
                }
            )

    def test_binding_a_connected_credential_to_another_service_is_refused(self):
        credential = self._credential()
        self.Connection.create(
            {
                "service_id": self.service.id,
                "credential_id": credential.id,
                "environment": "production",
            }
        )

        with self.assertRaises(ValidationError):
            credential.endpoint_id = self.other_service

    def test_the_base_url_follows_the_connection_environment_unless_overridden(self):
        connection = self._synced(self._credential(endpoint_id=self.service.id))

        self.assertEqual(connection._base_url(), "https://live.example.com")
        connection.environment = "test"
        self.assertEqual(connection._base_url(), "https://sandbox.example.com")
        connection.base_url = "https://device.example.com"
        self.assertEqual(connection._base_url(), "https://device.example.com")

    def test_a_credential_bound_nowhere_gets_no_connection(self):
        credential = self._credential()

        self.assertFalse(self.Connection._for_credential(self.service, credential))

    def test_a_credential_bound_to_another_service_gets_no_connection(self):
        credential = self._credential(endpoint_id=self.other_service.id)

        self.assertFalse(self.Connection._for_credential(self.service, credential))

    def test_migration_aligns_a_service_whose_connections_share_another_environment(
        self,
    ):
        self._credential(endpoint_id=self.service.id, environment="test")

        report = connect_bound_credentials(self.env)

        self.assertIn(self.service.code, report["aligned"])
        self.assertEqual(self.service.environment, "test")
        self.assertEqual(
            self.Connection._resolve(self.service)._base_url(),
            "https://sandbox.example.com",
        )

    def test_migration_reports_a_service_left_between_environments(self):
        self.service.allow_multiple_credentials = True
        self._credential(endpoint_id=self.service.id, environment="test")
        self._credential(endpoint_id=self.service.id, environment="staging")

        report = connect_bound_credentials(self.env)

        self.assertIn(self.service.code, report["unresolved"])
        self.assertEqual(self.service.environment, "production")


@tagged("post_install", "-at_install", "integration")
class TestPerRecordConnections(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Connection = cls.env["integration.connection"]
        cls.service = cls.env["integration.service"].create(
            {
                "name": "Panel probe",
                "code": "panel_probe",
                "auth_type": "digest",
                "environment": "production",
                "per_record_connections": True,
                "verify_tls": False,
                "allowed_hosts": "private",
            }
        )
        cls.login = cls.env["credential.credential"].create(
            {
                "name": "Panel probe login",
                "category_id": cls.env.ref(
                    "credential.credential_category_basic_auth"
                ).id,
                "username": "admin",
                "password": "panel-pass",
            }
        )

    def _panel(self, address, name="Door"):
        return self.Connection.create(
            {
                "name": name,
                "service_id": self.service.id,
                "credential_id": self.login.id,
                "company_id": self.env.company.id,
                "environment": "production",
                "base_url": f"https://{address}",
            }
        )

    def test_a_service_without_a_url_needs_per_record_connections(self):
        with self.assertRaises(ValidationError):
            self.service.per_record_connections = False

    def test_every_record_may_have_its_own_active_connection(self):
        first = self._panel("192.168.1.50", "Front door")
        second = self._panel("192.168.1.51", "Back door")

        self.assertTrue(first.active and second.active)
        self.assertEqual(first.display_name, "Panel probe · Front door")

    def test_no_connection_is_picked_by_company(self):
        self._panel("192.168.1.50")

        self.assertFalse(self.Connection._resolve(self.service))

    def test_a_call_on_a_connection_reaches_its_own_address_with_its_login(self):
        panel = self._panel("192.168.1.50")

        with patch("requests.Session.request") as request:
            request.return_value = _ok_response()
            panel._get_api_client().get("/ISAPI/System/deviceInfo")

        self.assertEqual(
            request.call_args.kwargs["url"],
            "https://192.168.1.50/ISAPI/System/deviceInfo",
        )
        self.assertIsInstance(request.call_args.kwargs["auth"], HTTPDigestAuth)

    def test_a_call_that_names_no_connection_is_refused(self):
        with self.assertRaises(CommError):
            get_api_client(self.env, "panel_probe")

    def test_a_connection_of_another_service_is_refused(self):
        other = self.env["integration.service"].create(
            {
                "name": "Other panel probe",
                "code": "other_panel_probe",
                "endpoint_url": "https://other.example.com",
            }
        )

        with self.assertRaises(CommError):
            get_api_client(
                self.env, other.code, connection_id=self._panel("192.168.1.50").id
            )

    def test_a_connection_may_not_leave_the_private_network_without_tls(self):
        with self.assertRaises(ValidationError):
            self._panel("8.8.8.8")
