from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError, ValidationError
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged

MODULE = "odoo.addons.google_recaptcha.models.ir_http"


@tagged("post_install", "-at_install")
class TestGoogleRecaptcha(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.icp = cls.env["ir.config_parameter"].sudo()

    @contextmanager
    def _mocked_verify(self, *, json_result=None, post_side_effect=None):
        """Run the verify helpers with a stubbed request and HTTP layer."""
        req = MagicMock()
        req.env = self.env
        req.httprequest.remote_addr = "10.0.0.1"
        req.params = {"recaptcha_token_response": "a-token"}
        with (
            patch(f"{MODULE}.request", req),
            patch.object(GuardedSession, "request") as post,
        ):
            if post_side_effect is not None:
                post.side_effect = post_side_effect
            else:
                post.return_value = MagicMock(**{"json.return_value": json_result})
            yield

    def _verify_token(self, **kwargs):
        with self._mocked_verify(**kwargs):
            return self.env["ir.http"]._get_recaptcha_verdict(
                "10.0.0.1", "a-token", action="login"
            )

    # ── _add_public_key_to_session_info ──────────────────────────────

    def test_public_key_added_when_enabled(self):
        """The public key is injected into session info when configured."""
        self.icp.set_param("recaptcha_public_key", "PUBKEY")
        self.icp.set_param("enable_recaptcha", "True")
        info = self.env["ir.http"]._add_public_key_to_session_info({})
        self.assertEqual(info["recaptcha_public_key"], "PUBKEY")

    def test_public_key_omitted_when_disabled(self):
        """A disabled reCAPTCHA keeps the public key out of session info."""
        self.icp.set_param("recaptcha_public_key", "PUBKEY")
        self.icp.set_param("enable_recaptcha", "False")
        info = self.env["ir.http"]._add_public_key_to_session_info({})
        self.assertNotIn("recaptcha_public_key", info)

    # ── _get_recaptcha_verdict ──────────────────────────────────────

    def test_the_private_key_setting_lives_in_the_vault(self):
        self.env["res.config.settings"].create(
            {"recaptcha_private_key": " SECRET "}
        ).execute()

        self.assertEqual(
            self.env["credential.credential"]._get_system_secret(
                "recaptcha_private_key"
            ),
            "SECRET",
        )
        self.assertFalse(self.icp.get_param("recaptcha_private_key"))
        self.assertEqual(
            self.env["res.config.settings"].default_get(["recaptcha_private_key"])[
                "recaptcha_private_key"
            ],
            "SECRET",
        )

    def test_verify_returns_no_secret_without_private_key(self):
        """Verification is a no-op ('no_secret') when no secret is configured."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", ""
        )
        self.assertEqual(
            self._verify_token(json_result={"success": True, "score": 0.9}),
            "no_secret",
        )

    def test_verify_human_on_high_score(self):
        """A successful high-score response is classified as human."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("recaptcha_min_score", "0.7")
        result = self._verify_token(
            json_result={"success": True, "score": 0.9, "action": "login"}
        )
        self.assertEqual(result, "is_human")

    def test_verify_bot_on_low_score(self):
        """A successful low-score response is classified as a bot."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("recaptcha_min_score", "0.7")
        result = self._verify_token(
            json_result={"success": True, "score": 0.1, "action": "login"}
        )
        self.assertEqual(result, "is_bot")

    def test_verify_wrong_secret_error_code(self):
        """An invalid-secret error code maps to 'wrong_secret'."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        result = self._verify_token(
            json_result={"success": False, "error-codes": ["invalid-input-secret"]}
        )
        self.assertEqual(result, "wrong_secret")

    def test_verify_timeout_on_request_timeout(self):
        """A request timeout maps to 'timeout'."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        result = self._verify_token(post_side_effect=requests.exceptions.Timeout())
        self.assertEqual(result, "timeout")

    def test_verify_bad_request_on_unexpected_error(self):
        """Any other request error maps to 'bad_request'."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        result = self._verify_token(post_side_effect=ValueError("boom"))
        self.assertEqual(result, "bad_request")

    # ── _check_request_recaptcha_token (raising wrapper) ────────────

    def test_request_verification_raises_on_wrong_secret(self):
        """The request wrapper raises ValidationError on an invalid secret."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("enable_recaptcha", "True")
        with self._mocked_verify(
            json_result={"success": False, "error-codes": ["invalid-input-secret"]}
        ):
            with self.assertRaises(ValidationError):
                self.env["ir.http"]._check_request_recaptcha_token("login")

    def test_verify_wrong_token_error_code(self):
        """An invalid-response error code maps to 'wrong_token'."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        result = self._verify_token(
            json_result={"success": False, "error-codes": ["invalid-input-response"]}
        )
        self.assertEqual(result, "wrong_token")

    def test_verify_timeout_error_code(self):
        """A timeout-or-duplicate error code maps to 'timeout'."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        result = self._verify_token(
            json_result={"success": False, "error-codes": ["timeout-or-duplicate"]}
        )
        self.assertEqual(result, "timeout")

    def test_verify_bad_request_error_code(self):
        """A bad-request error code maps to 'bad_request'."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        result = self._verify_token(
            json_result={"success": False, "error-codes": ["bad-request"]}
        )
        self.assertEqual(result, "bad_request")

    def test_verify_wrong_action_on_action_mismatch(self):
        """A successful response for a different action maps to 'wrong_action'."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("recaptcha_min_score", "0.7")
        result = self._verify_token(
            json_result={"success": True, "score": 0.9, "action": "signup"}
        )
        self.assertEqual(result, "wrong_action")

    def test_request_verification_skipped_when_disabled(self):
        """The request wrapper is a no-op when reCAPTCHA is disabled."""
        self.icp.set_param("enable_recaptcha", "False")
        with self._mocked_verify(json_result={"success": True, "score": 0.9}):
            self.assertIsNone(
                self.env["ir.http"]._check_request_recaptcha_token("login")
            )

    def test_request_verification_raises_usererror_on_bot(self):
        """The request wrapper raises UserError for suspicious (bot) activity."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("recaptcha_min_score", "0.7")
        self.icp.set_param("enable_recaptcha", "True")
        with self._mocked_verify(
            json_result={"success": True, "score": 0.1, "action": "login"}
        ):
            with self.assertRaises(UserError):
                self.env["ir.http"]._check_request_recaptcha_token("login")

    def test_settings_enable_recaptcha_roundtrip(self):
        """Saving then reading the settings round-trips the enable flag."""
        settings = self.env["res.config.settings"].create({"enable_recaptcha": False})
        settings.set_values()
        self.assertFalse(
            self.env["res.config.settings"].default_get(["enable_recaptcha"])[
                "enable_recaptcha"
            ]
        )

    def test_failed_verification_truncates_the_token_in_the_log(self):
        """The log must not grow with the caller-supplied token (R02).

        The token is a request parameter, bounded only by Odoo's 128 MB body
        cap, and this line runs once per failed verification on public routes.
        Logging it whole let the caller choose how much we write to disk.
        """
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("enable_recaptcha", "True")
        huge = "A" * 100_000
        payload = {"success": False, "error-codes": ["invalid-input-response"]}

        with (
            self._mocked_verify(json_result=payload),
            self.assertLogs(MODULE, level="WARNING") as captured,
        ):
            verdict = self.env["ir.http"]._get_recaptcha_verdict(
                "10.0.0.1", huge, action="login"
            )

        self.assertEqual(verdict, "wrong_token")
        logged = "".join(captured.output)
        self.assertNotIn(huge, logged, "the whole token reached the log")
        self.assertLess(len(logged), 500, "the log line grows with the caller's token")
        self.assertIn("invalid-input-response", logged, "keep the diagnostic")

    def test_failed_verification_without_a_token_still_logs(self):
        """An empty/False token must not break the truncation."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("enable_recaptcha", "True")
        with (
            self._mocked_verify(
                json_result={
                    "success": False,
                    "error-codes": ["missing-input-response"],
                }
            ),
            self.assertLogs(MODULE, level="WARNING"),
        ):
            verdict = self.env["ir.http"]._get_recaptcha_verdict(
                "10.0.0.1", False, action="login"
            )
        self.assertEqual(verdict, "wrong_token")

    def test_success_without_a_score_is_not_human(self):
        """A scoreless success must not be read as score 0 (R01).

        Google v3 always scores a successful verification. A success with no
        score means the response is not the one this code reads -- a v2 site
        key, say -- and `result.get("score", False)` used to let that through
        as the number 0, which is accepted at a threshold of 0.
        """
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("enable_recaptcha", "True")
        for threshold in ("0.7", "0.0"):
            with self.subTest(min_score=threshold):
                self.icp.set_param("recaptcha_min_score", threshold)
                verdict = self._verify_token(
                    json_result={"success": True, "action": "login"}
                )
                self.assertNotEqual(
                    verdict,
                    "is_human",
                    "a response carrying no score was accepted as human",
                )

    def test_success_without_a_score_logs_no_invented_score(self):
        """The log must not state a score Google never sent."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("enable_recaptcha", "True")
        self.icp.set_param("recaptcha_min_score", "0.7")
        with (
            self._mocked_verify(json_result={"success": True, "action": "login"}),
            self.assertLogs(MODULE, level="WARNING") as captured,
        ):
            self.env["ir.http"]._get_recaptcha_verdict(
                "10.0.0.1", "a-token", action="login"
            )
        self.assertNotIn("0.000000", "".join(captured.output))

    def test_scored_responses_are_unchanged(self):
        """The guard must not disturb a normal v3 response."""
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("enable_recaptcha", "True")
        self.icp.set_param("recaptcha_min_score", "0.7")
        self.assertEqual(
            self._verify_token(
                json_result={"success": True, "score": 0.9, "action": "login"}
            ),
            "is_human",
        )
        self.assertEqual(
            self._verify_token(
                json_result={"success": True, "score": 0.1, "action": "login"}
            ),
            "is_bot",
        )
        self.assertEqual(
            self._verify_token(
                json_result={"success": True, "score": 0.0, "action": "login"}
            ),
            "is_bot",
            "an explicit score of 0 is still a real score",
        )

    def test_bad_request_log_names_the_exception(self):
        """The catch-all must say what actually failed (R03).

        It logged a fixed string, so a TLS error, a JSON parse error and the
        KeyError this same clause catches when Google's response changes shape
        were all indistinguishable in the log.
        """
        self.env["credential.credential"]._set_system_secret(
            "recaptcha_private_key", "SECRET"
        )
        self.icp.set_param("enable_recaptcha", "True")
        with (
            self._mocked_verify(
                post_side_effect=ValueError("simulated upstream problem")
            ),
            self.assertLogs(MODULE, level="ERROR") as captured,
        ):
            verdict = self.env["ir.http"]._get_recaptcha_verdict(
                "10.0.0.1", "a-token", action="login"
            )
        self.assertEqual(verdict, "bad_request")
        self.assertIn("ValueError", "".join(captured.output))
