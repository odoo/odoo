import hashlib
import hmac
import importlib.util
from pathlib import Path

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


MIGRATION = Path(__file__).resolve().parents[1] / "migrations/1.2/post-migrate.py"


@tagged("post_install", "-at_install")
class TestWebhookSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        category = cls.env["credential.category"].search([], limit=1) or cls.env[
            "credential.category"
        ].create({"name": "Test", "code": "wh_test"})
        cls.secret = "supersecret123"
        cls.credential = cls.env["credential.credential"].create(
            {
                "name": "Webhook Secret",
                "category_id": category.id,
                "credential_value": cls.secret,
            }
        )
        cls.rule = cls.env["automation.rule"].create(
            {
                "name": "WH rule",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "trigger": "on_webhook",
                "auth_type": "hmac_sha256",
                "credential_id": cls.credential.id,
            }
        )
        cls.body = b'{"event": "test", "x": 1}'

    def _sig(self, key):
        return "sha256=" + hmac.new(key.encode(), self.body, hashlib.sha256).hexdigest()

    def test_hmac_valid(self):
        ok, status, _msg = self.rule._check_webhook_request(
            {"X-Hub-Signature-256": self._sig(self.secret)}, self.body, "1.2.3.4"
        )
        self.assertTrue(ok)
        self.assertEqual(status, 200)

    def test_hmac_invalid_and_missing(self):
        bad, status, _m = self.rule._check_webhook_request(
            {"X-Hub-Signature-256": self._sig("wrong")}, self.body, "1.2.3.4"
        )
        self.assertFalse(bad)
        self.assertEqual(status, 401)
        missing, status, _m = self.rule._check_webhook_request({}, self.body, "1.2.3.4")
        self.assertFalse(missing)
        self.assertEqual(status, 401)

    def test_ip_allowlist(self):
        self.rule.ip_whitelist = "10.0.0.0/8, 192.168.1.5"
        sig = {"X-Hub-Signature-256": self._sig(self.secret)}
        self.assertTrue(self.rule._check_webhook_request(sig, self.body, "10.5.5.5")[0])
        blocked = self.rule._check_webhook_request(sig, self.body, "1.2.3.4")
        self.assertFalse(blocked[0])
        self.assertEqual(blocked[1], 403)

    def test_payload_size_limit(self):
        self.rule.max_payload_size = 5
        res = self.rule._check_webhook_request(
            {"X-Hub-Signature-256": self._sig(self.secret)}, self.body, "1.2.3.4"
        )
        self.assertFalse(res[0])
        self.assertEqual(res[1], 413)

    def _new_rule(self, **vals):
        return self.env["automation.rule"].create(
            {
                "name": "new webhook",
                "model_id": self.env.ref("base.model_res_partner").id,
                "trigger": "on_webhook",
                **vals,
            }
        )

    def test_a_new_webhook_authenticates_with_a_generated_secret(self):
        rule = self._new_rule()

        self.assertEqual(rule.auth_type, "hmac_sha256")
        self.assertTrue(rule.rate_limit_enabled)
        secret = rule.credential_id._use_secret("test")
        self.assertGreaterEqual(len(secret), 40)
        self.assertFalse(rule._check_webhook_request({}, self.body, "1.2.3.4")[0])
        signed = {"X-Hub-Signature-256": self._sig(secret)}
        self.assertTrue(rule._check_webhook_request(signed, self.body, "1.2.3.4")[0])

    def test_two_rules_never_share_a_generated_secret(self):
        first, second = self._new_rule(), self._new_rule(name="other")

        self.assertNotEqual(first.credential_id, second.credential_id)

    def test_a_rule_left_open_on_purpose_still_answers(self):
        rule = self._new_rule(auth_type="none")

        self.assertFalse(rule.credential_id)
        self.assertTrue(rule._check_webhook_request({}, self.body, "1.2.3.4")[0])

    def test_unsigned_calls_run_during_the_audit_window_and_not_after(self):
        rule = self._new_rule()
        rule._start_webhook_audit_window()

        self.assertTrue(rule._check_webhook_request({}, self.body, "1.2.3.4")[0])
        rule.webhook_enforce_from = fields.Datetime.subtract(
            fields.Datetime.now(), seconds=1
        )
        self.assertFalse(rule._check_webhook_request({}, self.body, "1.2.3.4")[0])

    def test_a_new_secret_replaces_the_old_one(self):
        rule = self._new_rule()
        old = rule.credential_id._use_secret("test")

        rule.action_generate_webhook_secret()

        new = rule.credential_id._use_secret("test")
        self.assertNotEqual(old, new)
        stale = {"X-Hub-Signature-256": self._sig(old)}
        self.assertFalse(rule._check_webhook_request(stale, self.body, "1.2.3.4")[0])

    def test_the_upgrade_gives_open_rules_a_secret_and_thirty_days(self):
        rule = self._new_rule(auth_type="none")

        spec = importlib.util.spec_from_file_location(
            "automation_webhook_1_2", MIGRATION
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "1.1")

        self.assertEqual(rule.auth_type, "hmac_sha256")
        self.assertTrue(rule.credential_id)
        remaining = rule.webhook_enforce_from - fields.Datetime.now()
        self.assertEqual(round(remaining.total_seconds() / 86400), 30)
        self.assertTrue(rule._check_webhook_request({}, self.body, "1.2.3.4")[0])

    def _calls(self, rule):
        self.env.cr.precommit.run()
        return self.env["integration.exchange"].search(
            [("channel_id", "=", f"automation.rule,{rule.id}")]
        )

    def test_every_call_is_recorded_without_its_body_unless_asked(self):
        rule = self._new_rule(auth_type="none")

        rule._execute_webhook({"secret_field": "value"})

        call = self._calls(rule)
        self.assertEqual(len(call), 1)
        self.assertEqual(call.state, "success")
        self.assertFalse(call.request_payload)
        self.assertNotIn(rule.webhook_uuid, call.request_url)

    def test_a_failing_call_is_recorded_with_its_error(self):
        rule = self._new_rule(auth_type="none", record_getter="model.browse([])")

        with self.assertRaises(ValidationError):
            rule._execute_webhook({"id": 1})

        call = self._calls(rule)
        self.assertEqual(call.state, "failed")
        self.assertEqual(call.status_code, 500)
