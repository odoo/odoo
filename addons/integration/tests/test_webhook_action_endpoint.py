from unittest.mock import patch

from odoo.libs import netguard
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.integration.models.ir_actions_server import _EndpointDelivery

_MODULE = "odoo.addons.integration.models.ir_actions_server"


@tagged("post_install", "-at_install")
class TestWebhookActionEndpoint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["ir.model"]._get("res.partner")
        cls.partner = cls.env["res.partner"].create({"name": "webhook target"})
        cls.endpoint = cls.env["integration.service"].create(
            {
                "name": "receiver",
                "code": "wh_receiver",
                "endpoint_url": "https://example.com",
                "auth_type": "bearer",
                "retry_enabled": False,
            }
        )
        cls.env["credential.credential"].create(
            {
                "name": "receiver token",
                "endpoint_id": cls.endpoint.id,
                "category_id": cls.env.ref("credential.credential_category_custom").id,
                "bearer_token": "SECRETTOKEN",
            }
        )

    def _action(self, **vals):
        return self.env["ir.actions.server"].create(
            {
                "name": "notify",
                "model_id": self.model.id,
                "state": "webhook",
                "webhook_url": "https://example.com/hook",
                **vals,
            }
        )

    def test_without_an_endpoint_base_still_posts_directly(self):
        action = self._action()
        deliver = action._prepare_webhook_delivery(
            "https://example.com/hook", 1, "n(#1)", "x"
        )
        self.assertNotIsInstance(deliver, _EndpointDelivery)

    def test_the_delivery_holds_no_recordset(self):
        action = self._action(webhook_endpoint_id=self.endpoint.id)
        deliver = action._prepare_webhook_delivery(
            "https://example.com/hook", 5, "n(#1)", "x"
        )

        self.assertIsInstance(deliver, _EndpointDelivery)
        for name, value in vars(deliver).items():
            with self.subTest(attribute=name):
                self.assertIsInstance(
                    value,
                    (str, int, type(None), netguard.Policy),
                    f"{name} is a {type(value).__name__}; only plain values may "
                    f"cross into the postcommit hook",
                )

    def test_it_captures_what_the_client_will_need(self):
        action = self._action(webhook_endpoint_id=self.endpoint.id)
        deliver = action._prepare_webhook_delivery(
            "https://example.com/hook", 7, "n(#1)", "x"
        )

        self.assertEqual(deliver.endpoint_code, "wh_receiver")
        self.assertEqual(deliver.dbname, self.env.cr.dbname)
        self.assertEqual(deliver.company_id, self.env.company.id)
        self.assertEqual(deliver.uid, self.env.uid)
        self.assertEqual(deliver.timeout, 7)

    @mute_logger(_MODULE)
    def test_the_delivery_opens_its_own_cursor(self):
        action = self._action(webhook_endpoint_id=self.endpoint.id)
        deliver = action._prepare_webhook_delivery(
            "https://example.com/hook", 5, "n(#1)", "x"
        )

        with patch(f"{_MODULE}.Registry") as registry:
            deliver('{"a": 1}')

        registry.assert_called_once_with(self.env.cr.dbname)
        registry.return_value.cursor.assert_called_once()

    def test_the_request_carries_the_endpoint_credential(self):
        action = self._action(webhook_endpoint_id=self.endpoint.id)
        deliver = action._prepare_webhook_delivery(
            "https://example.com/hook", 5, "n(#1)", "x"
        )

        sent = {}

        def fake_request(method, url, headers=None, **kwargs):
            sent.update(method=method, url=url, headers=headers or {}, kwargs=kwargs)
            raise RuntimeError("stop before the network")

        with (
            patch(f"{_MODULE}.Registry") as registry,
            patch("requests.Session.request", side_effect=fake_request),
            mute_logger(_MODULE),
        ):
            registry.return_value.cursor.return_value.__enter__.return_value = (
                self.env.cr
            )
            deliver('{"a": 1}')

        self.assertEqual(sent["method"], "POST")
        self.assertEqual(
            sent["url"],
            "https://example.com/hook",
            "the action still owns where it points; the endpoint only supplies auth",
        )
        self.assertEqual(sent["headers"].get("Authorization"), "Bearer SECRETTOKEN")
        self.assertEqual(sent["headers"].get("Content-Type"), "application/json")

    def test_an_endpoint_that_retries_is_refused(self):
        retrying = self.env["integration.service"].create(
            {
                "name": "retries",
                "code": "wh_retries",
                "endpoint_url": "https://example.com",
                "auth_type": "none",
                "retry_enabled": True,
            }
        )
        with self.assertRaises(Exception) as caught:
            self._action(webhook_endpoint_id=retrying.id)
        self.assertIn("retry", str(caught.exception).lower())

    def test_a_non_webhook_action_cannot_carry_an_endpoint(self):
        with self.assertRaises(Exception):
            self.env["ir.actions.server"].create(
                {
                    "name": "code action",
                    "model_id": self.model.id,
                    "state": "code",
                    "code": "pass",
                    "webhook_endpoint_id": self.endpoint.id,
                }
            )

    @mute_logger(_MODULE)
    def test_the_guard_runs_again_at_delivery(self):
        action = self._action(webhook_endpoint_id=self.endpoint.id)
        deliver = action._prepare_webhook_delivery(
            "https://example.com/hook", 5, "n(#1)", "x"
        )

        with (
            patch(f"{_MODULE}.Registry") as registry,
            patch(
                "socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("127.0.0.1", 443))],
            ),
            mute_logger(_MODULE),
        ):
            deliver('{"a": 1}')

        registry.assert_not_called()

    def test_a_failed_delivery_does_not_escape_the_hook(self):
        action = self._action(webhook_endpoint_id=self.endpoint.id)
        deliver = action._prepare_webhook_delivery(
            "https://example.com/hook", 5, "n(#1)", "x"
        )

        with patch(f"{_MODULE}.Registry", side_effect=RuntimeError("no database")):
            deliver('{"a": 1}')
