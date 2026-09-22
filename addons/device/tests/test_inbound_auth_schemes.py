import hashlib
import hmac

from odoo.tools import mute_logger

from .common import DeviceTransactionCase


class TestInboundAuthSchemes(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile()

    def _device(self, auth_type, secret=None, **overrides):
        device = self._create_device_device(
            config=self.config,
            identifier=f"GATE-{auth_type.upper()}",
            auth_type=auth_type,
            rate_limit_enabled=False,
            **overrides,
        )
        if secret is not None:
            device.credential_id.sudo().credential_value = secret
            device.invalidate_recordset()
        return device

    def test_bearer_is_unchanged(self):
        device = self._device("bearer")
        token = self._device_token(device)

        allowed, reason = device.check_inbound_auth(
            {"Authorization": f"Bearer {token}"}, "10.0.0.1"
        )
        self.assertTrue(allowed, reason)

        allowed, _ = device.check_inbound_auth(
            {"Authorization": "Bearer wrong"}, "10.0.0.1"
        )
        self.assertFalse(allowed)

    def test_hmac_accepts_a_valid_signature(self):
        device = self._device(
            "hmac_sha256",
            secret="SHARED",
            signature_header="X-Hub-Signature-256",
            signature_prefix="sha256=",
        )
        body = b'{"event": "ping"}'
        digest = hmac.new(b"SHARED", body, hashlib.sha256).hexdigest()

        allowed, reason = device.check_inbound_auth(
            {"X-Hub-Signature-256": f"sha256={digest}"}, "10.0.0.1", body=body
        )
        self.assertTrue(
            allowed,
            f"an HMAC device used to be checked as a bearer token and rejected "
            f"whatever it sent; got {reason!r}",
        )

    def test_hmac_rejects_a_forged_signature(self):
        device = self._device(
            "hmac_sha256",
            secret="SHARED",
            signature_header="X-Hub-Signature-256",
            signature_prefix="sha256=",
        )
        allowed, _ = device.check_inbound_auth(
            {"X-Hub-Signature-256": "sha256=deadbeef"}, "10.0.0.1", body=b"{}"
        )
        self.assertFalse(allowed)

    def test_hmac_without_a_body_names_the_omission(self):
        device = self._device(
            "hmac_sha256",
            secret="SHARED",
            signature_header="X-Hub-Signature-256",
            signature_prefix="sha256=",
        )
        allowed, reason = device.check_inbound_auth(
            {"X-Hub-Signature-256": "sha256=whatever"}, "10.0.0.1"
        )
        self.assertFalse(allowed)
        self.assertIn(
            "verifies the request body",
            reason,
            "a caller that forgot body= must be told so, not handed the generic "
            "'unauthenticated request' a wrong secret also produces",
        )

    def test_the_gate_writes_nothing_per_request(self):
        device = self._device("bearer")
        token = self._device_token(device)
        credential = device.credential_id.sudo()
        self.env.flush_all()

        log = self.env["credential.access.log"].sudo()
        before = log.search_count([("credential_id", "=", credential.id)])

        for _ in range(5):
            allowed, reason = device.check_inbound_auth(
                {"Authorization": f"Bearer {token}"}, "10.0.0.1"
            )
            self.assertTrue(allowed, reason)
        self.env.flush_all()

        self.assertEqual(
            log.search_count([("credential_id", "=", credential.id)]),
            before,
            "five authentications must not add five audit rows to a fleet's "
            "hottest path",
        )

    def test_authenticate_request_still_marks_usage(self):
        device = self._device("bearer")
        token = self._device_token(device)
        credential = device.credential_id.sudo()

        self.assertTrue(
            device.authenticate_request({"Authorization": f"Bearer {token}"})
        )
        self.assertTrue(
            credential.last_used_at,
            "the request-per-event path keeps the side effect it always had",
        )

    def test_off_mode_short_circuits_before_any_check(self):
        device = self._device("hmac_sha256", secret="SHARED")
        allowed, _ = device.check_inbound_auth({}, "10.0.0.1", mode="off")
        self.assertTrue(allowed)

    @mute_logger("odoo.addons.integration.models.mixin_integration_receiver")
    def test_audit_mode_admits_an_unverifiable_request(self):
        device = self._device("hmac_sha256", secret="SHARED")
        allowed, _ = device.check_inbound_auth({}, "10.0.0.1", body=b"{}", mode="audit")
        self.assertTrue(allowed, "audit mode admits while a rollout completes")
