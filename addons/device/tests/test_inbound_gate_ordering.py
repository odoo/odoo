from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import DeviceTransactionCase
from odoo.addons.rate_limit.tools import get_caller_rate_limiter

MUTED = mute_logger(
    "odoo.addons.integration.models.mixin_inbound_gate",
    "odoo.addons.rate_limit.tools.caller_rate_limiter",
)


@tagged("post_install", "-at_install")
class TestInboundGateOrdering(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile()

    def setUp(self):
        super().setUp()
        get_caller_rate_limiter(self.env)._attempts.clear()
        self.env["ir.config_parameter"].sudo().set_param(
            "credential.inbound_preauth_multiplier", "10"
        )

    def _device(self, **overrides):
        device = self._create_device_device(
            config=self.config,
            identifier="GATE-ORDER",
            auth_type="bearer",
            rate_limit_enabled=True,
            rate_limit_requests=5,
            rate_limit_window_seconds=60,
            **overrides,
        )
        device.invalidate_recordset()
        return device

    def _push(self, device, token, addr="10.0.0.1"):
        return device.check_inbound_auth({"Authorization": f"Bearer {token}"}, addr)

    @MUTED
    def test_a_flood_of_wrong_tokens_does_not_lock_out_the_right_one(self):
        device = self._device()
        token = self._device_token(device)

        for attempt in range(5):
            allowed, _ = self._push(device, "WRONG-TOKEN", addr="203.0.113.9")
            self.assertFalse(allowed, f"wrong token {attempt + 1} must be refused")

        allowed, reason = self._push(device, token)
        self.assertTrue(
            allowed,
            f"the legitimate device was locked out by someone else's failed "
            f"attempts ({reason!r}) — the endpoint quota is being spent before "
            f"authentication",
        )

    @MUTED
    def test_the_endpoint_quota_still_binds_authenticated_callers(self):
        device = self._device()
        token = self._device_token(device)

        outcomes = [self._push(device, token)[0] for _ in range(8)]
        self.assertTrue(outcomes[0], "the first push must be accepted")
        self.assertIn(
            False,
            outcomes,
            "an authenticated caller must still run out of endpoint quota",
        )

    @MUTED
    def test_the_caller_guard_stops_an_unbounded_stranger(self):
        device = self._device()
        self.env["ir.config_parameter"].sudo().set_param(
            "credential.inbound_preauth_multiplier", "2"
        )

        outcomes = [
            self._push(device, "WRONG-TOKEN", addr="203.0.113.9")[1] for _ in range(14)
        ]
        self.assertTrue(
            any("caller rate limit" in reason for reason in outcomes),
            "a stranger sending wrong tokens for ever must eventually be "
            "refused before the signature work is done",
        )

    @MUTED
    def test_the_caller_guard_is_per_caller(self):
        device = self._device()
        token = self._device_token(device)
        self.env["ir.config_parameter"].sudo().set_param(
            "credential.inbound_preauth_multiplier", "2"
        )

        for _ in range(14):
            self._push(device, "WRONG-TOKEN", addr="203.0.113.9")

        allowed, reason = self._push(device, token, addr="10.0.0.1")
        self.assertTrue(
            allowed,
            f"the guard is keyed on the caller, so a flood from one address "
            f"must not refuse another ({reason!r})",
        )

    @MUTED
    def test_disabling_the_multiplier_disables_the_caller_guard(self):
        device = self._device()
        self.env["ir.config_parameter"].sudo().set_param(
            "credential.inbound_preauth_multiplier", "0"
        )

        outcomes = [
            self._push(device, "WRONG-TOKEN", addr="203.0.113.9")[1] for _ in range(30)
        ]
        self.assertFalse(
            any("caller rate limit" in reason for reason in outcomes),
            "0 must switch the pre-authentication guard off entirely",
        )
