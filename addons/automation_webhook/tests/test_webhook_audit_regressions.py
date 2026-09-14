import hashlib
import hmac
import json

from odoo.tests import HttpCase, tagged

from odoo.addons.automation.tests.test_audit_regressions import AutomationAuditCommon


@tagged("post_install", "-at_install")
class TestRecordlessWebhookRespectsDependencies(AutomationAuditCommon):
    def test_recordless_webhook_respects_dependency_order_too(self):
        automation = self._automation(
            "recordless webhook", trigger="on_webhook", webhook_uuid="test-uuid-order"
        )
        first = self._action(
            automation,
            "first",
            sequence=50,
            code="env['res.partner'].create({'name': 'order-marker', 'ref': 'A'})",
        )
        self._action(
            automation,
            "second",
            sequence=10,
            code="env['res.partner'].create({'name': 'order-marker', 'ref': 'B'})",
            predecessors=[first],
        )

        automation._execute_webhook({})

        markers = self.env["res.partner"].search(
            [("name", "=", "order-marker")], order="id"
        )
        self.assertEqual(
            markers.mapped("ref"),
            ["A", "B"],
            "sequence must not override the graph on the recordless webhook path either",
        )


@tagged("post_install", "-at_install")
class TestWebhookOverHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_partner = cls.env["ir.model"]._get("res.partner")
        cls.secret = "audit-secret"
        category = cls.env["credential.category"].search([], limit=1) or cls.env[
            "credential.category"
        ].create({"name": "A", "code": "audit"})
        cls.credential = cls.env["credential.credential"].create(
            {
                "name": "audit secret",
                "category_id": category.id,
                "credential_value": cls.secret,
            }
        )
        cls.body = b'{"audit": true}'
        cls.signature = (
            "sha256="
            + hmac.new(
                cls.secret.encode(),
                cls.body,
                hashlib.sha256,
            ).hexdigest()
        )

    def _rule(self, name, **kw):
        rule = self.env["automation.rule"].create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "trigger": "on_webhook",
                **kw,
            }
        )
        self.env["ir.actions.server"].create(
            {
                "name": f"{name}-action",
                "model_id": self.model_partner.id,
                "state": "code",
                "usage": "automation",
                "automation_rule_id": rule.id,
                "code": (
                    "env['ir.config_parameter'].sudo()"
                    ".set_param('automation.webhook_probe', 'fired')"
                ),
            }
        )
        return rule

    def _post(self, rule, headers=None):
        return self.url_open(
            f"/web/hook/{rule.webhook_uuid}",
            data=self.body,
            headers={"Content-Type": "application/json", **(headers or {})},
        )

    def test_signature_header_name_is_case_insensitive(self):
        for configured in (
            "x-hub-signature-256",
            "X-HUB-SIGNATURE-256",
            "X-Hub-Signature-256",
        ):
            rule = self._rule(
                f"hdr-{configured}",
                auth_type="hmac_sha256",
                credential_id=self.credential.id,
                signature_header=configured,
            )
            response = self._post(rule, {"X-Hub-Signature-256": self.signature})
            self.assertEqual(
                response.status_code,
                200,
                f"a valid request was rejected for header spelling {configured!r}",
            )

    def test_bad_signature_is_still_rejected(self):
        rule = self._rule(
            "bad-sig",
            auth_type="hmac_sha256",
            credential_id=self.credential.id,
        )
        response = self._post(rule, {"X-Hub-Signature-256": "sha256=deadbeef"})
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_calls_cannot_exhaust_the_rate_limit(self):
        rule = self._rule(
            "rate",
            auth_type="hmac_sha256",
            credential_id=self.credential.id,
            rate_limit_enabled=True,
            rate_limit_requests=3,
            rate_limit_window_seconds=60,
        )
        for _ in range(6):
            self.assertEqual(
                self._post(
                    rule, {"X-Hub-Signature-256": "sha256=deadbeef"}
                ).status_code,
                401,
                "unsigned calls must be refused before they spend a token",
            )
        self.assertEqual(
            self._post(rule, {"X-Hub-Signature-256": self.signature}).status_code,
            200,
            "the legitimate sender was locked out by unauthenticated traffic",
        )

    def test_non_webhook_rule_is_not_reachable(self):
        rule = self.env["automation.rule"].create(
            {
                "name": "not a webhook",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
            }
        )
        self.env["ir.actions.server"].create(
            {
                "name": "should not run",
                "model_id": self.model_partner.id,
                "state": "code",
                "usage": "automation",
                "automation_rule_id": rule.id,
                "code": (
                    "env['ir.config_parameter'].sudo()"
                    ".set_param('automation.webhook_probe', 'fired')"
                ),
            }
        )
        parameters = self.env["ir.config_parameter"].sudo()
        parameters.set_param("automation.webhook_probe", "no")

        response = self.url_open(
            f"/web/hook/{rule.webhook_uuid}",
            data=json.dumps({"x": 1}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(
            response.status_code,
            404,
            "a non-webhook rule must not resolve to an endpoint at all",
        )
        self.env.invalidate_all()
        self.assertEqual(
            parameters.get_param("automation.webhook_probe"),
            "no",
            "a non-webhook rule ran over HTTP",
        )
