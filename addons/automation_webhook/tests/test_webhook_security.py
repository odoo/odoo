import hashlib
import hmac

from odoo.tests import TransactionCase, tagged

from odoo.addons.mixin_encryption.tests.common import EncryptionKeyCase


@tagged("post_install", "-at_install")
class TestWebhookSecurity(EncryptionKeyCase, TransactionCase):
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

    def test_none_auth_is_open_by_default(self):
        rule = self.env["automation.rule"].create(
            {
                "name": "open",
                "model_id": self.env.ref("base.model_res_partner").id,
                "trigger": "on_webhook",
            }
        )
        self.assertTrue(rule._check_webhook_request({}, self.body, "1.2.3.4")[0])
