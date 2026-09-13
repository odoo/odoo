from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.mixin_encryption.tests.common import EncryptionKeyCase


@tagged("post_install", "-at_install")
class TestWebhookAuthDoesNotExhaustTheDecryptionCap(EncryptionKeyCase, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["credential.credential"].create(
            {
                "name": "webhook decrypt-budget probe secret",
                "category_id": cls.env.ref(
                    "credential.credential_category_bearer_token"
                ).id,
                "credential_value": "HOOKSECRET",
            }
        )
        model = cls.env["ir.model"]._get("res.partner")
        action = cls.env["ir.actions.server"].create(
            {
                "name": "webhook budget probe action",
                "model_id": model.id,
                "state": "code",
                "code": "pass",
            }
        )
        cls.rule = cls.env["automation.rule"].create(
            {
                "name": "webhook budget probe",
                "model_id": model.id,
                "trigger": "on_webhook",
                "action_server_ids": [(6, 0, action.ids)],
                "auth_type": "bearer",
                "credential_id": cls.credential.id,
                "rate_limit_enabled": False,
                "record_getter": "",
            }
        )

    def _fresh_request(self):
        self.credential.invalidate_recordset()

    def _verify(self):
        return self.rule._check_webhook_request(
            headers={"Authorization": "Bearer HOOKSECRET"},
            body=b'{"ping": 1}',
            remote_addr="10.0.0.1",
        )

    def test_a_low_cap_does_not_stop_the_webhook(self):
        self.credential.sudo().write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 3}
        )
        self.env.flush_all()

        for attempt in range(1, 26):
            self._fresh_request()
            ok, status, message = self._verify()
            self.assertTrue(
                ok,
                f"call {attempt} was refused ({status}: {message}); an "
                f"authenticated webhook must not have a per-hour ceiling",
            )

    def test_a_wrong_secret_is_still_refused(self):
        ok, status, _ = self.rule._check_webhook_request(
            headers={"Authorization": "Bearer WRONG"},
            body=b'{"ping": 1}',
            remote_addr="10.0.0.1",
        )
        self.assertFalse(ok, "lifting the cap must not lift the authentication")
        self.assertEqual(status, 401)

    @mute_logger("odoo.addons.credential.models.credential_credential")
    def test_verification_writes_no_audit_rows(self):
        log = self.env["credential.access.log"].sudo()
        self.env.flush_all()
        before = log.search_count([("credential_id", "=", self.credential.id)])

        for _ in range(10):
            self._fresh_request()
            ok, _, _ = self._verify()
            self.assertTrue(ok)
        self.env.flush_all()

        self.assertEqual(
            log.search_count([("credential_id", "=", self.credential.id)]),
            before,
            "ten webhook deliveries used to leave ten 'read' rows describing "
            "traffic that was never suspicious",
        )

    def test_hmac_webhooks_are_covered_too(self):
        import hashlib
        import hmac as hmac_mod

        self.rule.write(
            {
                "auth_type": "hmac_sha256",
                "signature_header": "X-Hub-Signature-256",
                "signature_prefix": "sha256=",
            }
        )
        self.credential.sudo().write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 3}
        )
        self.env.flush_all()

        body = b'{"ping": 1}'
        digest = hmac_mod.new(b"HOOKSECRET", body, hashlib.sha256).hexdigest()
        for attempt in range(1, 16):
            self._fresh_request()
            ok, status, message = self.rule._check_webhook_request(
                headers={"X-Hub-Signature-256": f"sha256={digest}"},
                body=body,
                remote_addr="10.0.0.1",
            )
            self.assertTrue(ok, f"HMAC call {attempt} refused ({status}: {message})")
