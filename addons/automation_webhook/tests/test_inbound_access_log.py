from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.integration.models import mixin_inbound_gate
from odoo.addons.integration.tests.common import open_admission

_GATE = "odoo.addons.integration.models.mixin_inbound_gate"


@tagged("post_install", "-at_install")
class TestInboundRefusals(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rows = cls.env["integration.exchange"].sudo()
        cls.model_id = cls.env.ref("base.model_res_partner").id

    def setUp(self):
        super().setUp()
        mixin_inbound_gate._STANDING_CONDITIONS_REPORTED.clear()

    def _endpoint(self, code, **vals):
        endpoint = self.env["automation.rule"].create(
            {
                "name": code,
                "model_id": self.model_id,
                "trigger": "on_webhook",
                "auth_type": "bearer",
                **vals,
            }
        )
        endpoint.credential_id = False
        return endpoint

    _GOOD_TOKEN = "the-token-the-caller-should-have-sent"

    def _credentialed_endpoint(self, code, **vals):
        endpoint = self._endpoint(code, **vals)
        endpoint.credential_id = self.env["credential.credential"].create(
            {
                "name": f"{code} token",
                "category_id": self.env.ref(
                    "credential.credential_category_bearer_token"
                ).id,
                "credential_value": self._GOOD_TOKEN,
            }
        )
        return endpoint

    def _rows(self, endpoint):
        return self.rows.search(
            [("channel_id", "=", f"{endpoint._name},{endpoint.id}")]
        )

    def _refusals(self, endpoint):
        return self._rows(endpoint).filtered(lambda row: row.state == "refused")

    def test_a_refusal_is_recorded(self):
        endpoint = self._credentialed_endpoint("gate_refused")

        allowed, status, _reason = endpoint._check_inbound_request(
            {"Authorization": "Bearer wrong"}, remote_addr="203.0.113.7"
        )

        self.assertFalse(allowed)
        row = self._refusals(endpoint)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.refusal_reason, "authentication_failed")
        self.assertEqual(row.status_code, status)
        self.assertEqual(row.source_ip, "203.0.113.7")
        self.assertEqual(row.attempt_count, 1)
        self.assertEqual(row.auth_mode, "enforce")
        self.assertFalse(row.is_success)

    def test_the_verdict_s_code_is_the_problem_document_s(self):
        endpoint = self._credentialed_endpoint("gate_code")
        verdict = endpoint._inbound_verdict(
            {"Authorization": "Bearer wrong"}, remote_addr="203.0.113.7"
        )
        self.assertEqual(
            (verdict.allowed, verdict.status, verdict.code),
            (False, 401, "authentication_failed"),
        )
        self.assertEqual(self._refusals(endpoint).refusal_reason, verdict.code)

    @mute_logger(_GATE)
    def test_the_row_survives_the_endpoint(self):
        endpoint = self._endpoint("gate_deleted")
        endpoint._check_inbound_request({}, remote_addr="203.0.113.8")
        row = self._refusals(endpoint)
        self.assertEqual(row.channel_name, endpoint.display_name)

        endpoint.unlink()
        row.invalidate_recordset()
        self.assertTrue(row.exists())
        self.assertTrue(row.channel_name, "the snapshot is what makes it readable")

    def test_two_different_bad_tokens_are_two_facts(self):
        endpoint = self._credentialed_endpoint("gate_two_tokens")
        endpoint._check_inbound_request(
            {"Authorization": "Bearer one"}, remote_addr="203.0.113.9"
        )
        endpoint._check_inbound_request(
            {"Authorization": "Bearer two"}, remote_addr="203.0.113.9"
        )
        rows = self._refusals(endpoint)
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows.mapped("refusal_reason")), {"authentication_failed"})

    def test_the_right_token_is_admitted_and_the_verdict_leaves_no_row(self):
        endpoint = self._credentialed_endpoint("gate_good_token")

        allowed, status, _reason = endpoint._check_inbound_request(
            {"Authorization": f"Bearer {self._GOOD_TOKEN}"},
            remote_addr="203.0.113.20",
        )

        self.assertTrue(allowed)
        self.assertEqual(status, 200)
        self.assertFalse(self._rows(endpoint), "the admission writes its own row")

    def test_an_admission_is_the_admission_s_row(self):
        endpoint = self._endpoint("gate_admitted", auth_type="none")

        admission = open_admission(endpoint, path="/web/hook/x")

        self.assertEqual(self._rows(endpoint), admission.exchange)
        self.assertEqual(admission.exchange.auth_mode, "enforce")

    def test_a_gate_that_is_off_records_nothing(self):
        endpoint = self._endpoint("gate_off")

        endpoint._check_inbound_request({}, mode=endpoint.AUTH_MODE_OFF)

        self.assertFalse(self._rows(endpoint))

    @mute_logger(_GATE)
    def test_audit_mode_admits_and_the_admission_says_so(self):
        endpoint = self._endpoint("gate_audit")

        verdict = endpoint._inbound_verdict({}, mode=endpoint.AUTH_MODE_AUDIT)
        self.assertTrue(verdict.allowed)
        self.assertEqual(verdict.code, "audit_accepted")
        self.assertIn("No credential configured", verdict.reason)
        self.assertFalse(self._rows(endpoint), "no verdict row: the admission's")

        admission = open_admission(endpoint, path="/web/hook/x")
        admission.auth_mode = "audit"
        admission.exchange.unlink()
        endpoint._open_inbound_exchange(admission, "webhook")
        self.assertEqual(admission.exchange.auth_mode, "audit")
        self.assertFalse(admission.exchange.signature_verified)

    def test_repeated_caller_limit_refusals_collapse(self):
        endpoint = self._endpoint("gate_flood")

        with patch.object(
            type(endpoint),
            "_check_inbound_caller",
            return_value=(False, 429, "caller rate limit"),
        ):
            for _ in range(25):
                endpoint._check_inbound_request({}, remote_addr="198.51.100.4")

        rows = self._refusals(endpoint)
        self.assertEqual(len(rows), 1, "25 refusals must not be 25 rows")
        self.assertEqual(rows.refusal_reason, "caller_limited")
        self.assertEqual(rows.attempt_count, 25)
        self.assertGreaterEqual(rows.last_seen_at, rows.timestamp)
        self.assertIn("×25", rows.display_name)

    def test_the_collapse_is_per_caller(self):
        endpoint = self._endpoint("gate_flood_two")

        with patch.object(
            type(endpoint),
            "_check_inbound_caller",
            return_value=(False, 429, "caller rate limit"),
        ):
            for address in ("198.51.100.5", "198.51.100.6", "198.51.100.5"):
                endpoint._check_inbound_request({}, remote_addr=address)

        rows = self._refusals(endpoint)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted(rows.mapped("attempt_count")), [1, 2])

    @mute_logger(_GATE)
    def test_a_distinguishable_refusal_does_not_collapse(self):
        endpoint = self._credentialed_endpoint("gate_no_collapse")

        for _ in range(3):
            endpoint._check_inbound_request(
                {"Authorization": "Bearer nope"}, remote_addr="198.51.100.7"
            )

        self.assertEqual(len(self._refusals(endpoint)), 3)

    def test_a_bad_token_refusal_is_recorded_but_not_logged(self):
        endpoint = self._credentialed_endpoint("gate_quiet_refusal")

        with self.assertNoLogs(_GATE, "WARNING"):
            endpoint._check_inbound_request(
                {"Authorization": "Bearer nope"}, remote_addr="198.51.100.21"
            )

        self.assertEqual(
            self._refusals(endpoint).refusal_reason, "authentication_failed"
        )

    def test_a_standing_audit_condition_is_reported_once(self):
        endpoint = self._endpoint("gate_audit_quiet")

        with self.assertLogs(_GATE, "WARNING") as logs:
            for n in range(30):
                endpoint._check_inbound_request(
                    {},
                    remote_addr=f"198.51.100.{n + 100}",
                    mode=endpoint.AUTH_MODE_AUDIT,
                )

        self.assertEqual(
            len(logs.output), 1, "one unprovisioned gate is one thing to say"
        )
        self.assertIn("UNAUTHENTICATED request accepted", logs.output[0])
        self.assertFalse(self._rows(endpoint), "and nothing to write")

    def test_two_gates_in_audit_mode_are_two_conditions(self):
        one = self._endpoint("gate_audit_one")
        two = self._endpoint("gate_audit_two")

        with self.assertLogs(_GATE, "WARNING") as logs:
            for endpoint in (one, two, one):
                endpoint._check_inbound_request(
                    {}, remote_addr="198.51.100.12", mode=endpoint.AUTH_MODE_AUDIT
                )

        self.assertEqual(len(logs.output), 2)

    def test_an_enforced_refusal_is_recorded_not_logged(self):
        endpoint = self._credentialed_endpoint("gate_single_line")

        with self.assertNoLogs(_GATE, "WARNING"):
            endpoint._check_inbound_request({}, remote_addr="198.51.100.13")

        self.assertTrue(self._refusals(endpoint).error_message)

    def test_a_garbage_window_parameter_still_collapses(self):
        endpoint = self._endpoint("gate_bad_param")
        params = self.env["ir.config_parameter"].sudo()

        for value in ("not-a-number", "0", "-1"):
            params.set_param(endpoint.STANDING_WINDOW_PARAM, value)
            self.assertGreaterEqual(
                endpoint._get_inbound_coalesce_window("misconfigured"), 60
            )

        with mute_logger(_GATE):
            for _ in range(5):
                endpoint._check_inbound_request({}, remote_addr="198.51.100.30")
        self.assertEqual(len(self._refusals(endpoint)), 1)

    def test_the_caller_limit_window_is_the_limiter_s_own(self):
        endpoint = self._endpoint("gate_window_split", rate_limit_window_seconds=45)
        self.env["ir.config_parameter"].sudo().set_param(
            endpoint.STANDING_WINDOW_PARAM, "7200"
        )

        self.assertEqual(endpoint._get_inbound_coalesce_window("caller_limited"), 45)
        self.assertEqual(endpoint._get_inbound_coalesce_window("misconfigured"), 7200)

    @mute_logger(_GATE)
    def test_a_gate_with_no_credential_is_misconfigured_not_unauthenticated(self):
        endpoint = self._endpoint("gate_no_cred")

        allowed, status, _reason = endpoint._check_inbound_request(
            {"Authorization": "Bearer anything"}, remote_addr="198.51.100.40"
        )

        self.assertFalse(allowed)
        self.assertEqual(status, 401, "the wire contract is unchanged")
        row = self._refusals(endpoint)
        self.assertEqual(row.refusal_reason, "misconfigured")
        self.assertIn("No credential configured", row.error_message)

    @mute_logger(_GATE)
    def test_a_body_dependent_gate_asked_without_a_body_is_misconfigured(self):
        endpoint = self._credentialed_endpoint(
            "gate_hmac_no_body", auth_type="hmac_sha256"
        )

        allowed, _status, _reason = endpoint._check_inbound_request(
            {}, body=None, remote_addr="198.51.100.41"
        )

        self.assertFalse(allowed)
        self.assertEqual(self._refusals(endpoint).refusal_reason, "misconfigured")

    @mute_logger(_GATE)
    def test_a_misconfigured_gate_collapses_per_gate(self):
        endpoint = self._endpoint("gate_no_cred_flood")

        for n in range(30):
            endpoint._check_inbound_request({}, remote_addr=f"198.51.100.{n + 60}")

        rows = self._refusals(endpoint)
        self.assertEqual(len(rows), 1, "30 requests, one broken gate")
        self.assertEqual(rows.refusal_reason, "misconfigured")

    def test_a_misconfigured_gate_is_reported_once_and_loudly(self):
        endpoint = self._endpoint("gate_no_cred_quiet")

        with self.assertLogs(_GATE, "ERROR") as logs:
            for _ in range(20):
                endpoint._check_inbound_request({}, remote_addr="198.51.100.42")

        self.assertEqual(len(logs.output), 1)
        self.assertIn("refusing EVERY request", logs.output[0])

    @mute_logger(_GATE)
    def test_a_misconfigured_gate_row_is_not_counted(self):
        endpoint = self._endpoint("gate_no_cred_no_write")
        endpoint._check_inbound_request({}, remote_addr="198.51.100.43")
        row = self._refusals(endpoint)

        with patch.object(type(row), "write", autospec=True) as write:
            for _ in range(10):
                endpoint._check_inbound_request({}, remote_addr="198.51.100.43")

        write.assert_not_called()
        self.assertEqual(row.attempt_count, 1)

    @mute_logger(_GATE)
    def test_audit_mode_still_wins_over_the_gate_fault(self):
        endpoint = self._endpoint("gate_no_cred_audit")

        verdict = endpoint._inbound_verdict(
            {}, mode=endpoint.AUTH_MODE_AUDIT, remote_addr="198.51.100.44"
        )

        self.assertTrue(verdict.allowed)
        self.assertEqual(verdict.code, "audit_accepted")
        self.assertIn("No credential configured", verdict.reason)

    @mute_logger(_GATE)
    def test_a_failure_to_record_does_not_change_the_verdict(self):
        endpoint = self._credentialed_endpoint("gate_log_broken")

        with patch.object(
            type(endpoint),
            "_store_inbound_refusal",
            side_effect=RuntimeError("table is gone"),
        ):
            allowed, status, _reason = endpoint._check_inbound_request(
                {"Authorization": "Bearer wrong"}, remote_addr="203.0.113.10"
            )

        self.assertFalse(allowed)
        self.assertEqual(status, 401)

    @mute_logger(_GATE)
    def test_the_refusal_cannot_be_edited(self):
        endpoint = self._endpoint("gate_immutable")
        endpoint._check_inbound_request({}, remote_addr="203.0.113.11")
        row = self._refusals(endpoint)

        with self.assertRaises(UserError):
            row.write({"error_message": "something else"})
        with self.assertRaises(UserError):
            row.unlink()

    @mute_logger(_GATE)
    def test_the_retention_sweep_may_delete(self):
        endpoint = self._endpoint("gate_retention")
        endpoint._check_inbound_request({}, remote_addr="203.0.113.12")
        row = self._refusals(endpoint)
        self.assertTrue(row)
        self.env["ir.config_parameter"].sudo().set_param(
            "integration.log_retention_days", "1"
        )
        row.with_context(**{row._CLEANUP_CONTEXT_KEY: True}).sudo().write(
            {"date_completed": row.date_completed.replace(year=2001)}
        )

        self.rows._gc_old_logs()

        self.assertFalse(self._refusals(endpoint))


@tagged("post_install", "-at_install")
class TestInboundRateLimitScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env.ref("base.model_res_partner").id
        cls.company_a = cls.env["res.company"].create({"name": "Gate Scope A"})
        cls.company_b = cls.env["res.company"].create({"name": "Gate Scope B"})
        cls.buckets = cls.env["rate.limit.bucket"].sudo()

    def _endpoint(self, code, allowed):
        return self.env["automation.rule"].create(
            {
                "name": code,
                "model_id": self.model_id,
                "trigger": "on_webhook",
                "auth_type": "none",
                "rate_limit_enabled": True,
                "rate_limit_requests": allowed,
            }
        )

    def _keys(self, endpoint):
        return self.buckets.search(
            [
                ("endpoint_model", "=", endpoint._name),
                ("endpoint_id", "=", endpoint.id),
            ]
        ).mapped("bucket_key")

    def test_switching_company_does_not_buy_a_fresh_allowance(self):
        endpoint = self._endpoint("gate_scope_bypass", allowed=2)

        self.assertTrue(endpoint.with_company(self.company_a).check_rate_limit())
        self.assertTrue(endpoint.with_company(self.company_a).check_rate_limit())
        self.assertFalse(
            endpoint.with_company(self.company_a).check_rate_limit(),
            "the endpoint's own allowance is spent",
        )

        self.assertFalse(
            endpoint.with_company(self.company_b).check_rate_limit(),
            "a different active company must NOT reset the endpoint's quota",
        )

    def test_one_endpoint_keeps_one_bucket_across_companies(self):
        endpoint = self._endpoint("gate_scope_single", allowed=5)

        endpoint.with_company(self.company_a).check_rate_limit()
        endpoint.with_company(self.company_b).check_rate_limit()

        self.assertEqual(
            self._keys(endpoint),
            [f"automation.rule:{endpoint.id}:global"],
            "automation.rule carries no company_id, so the endpoint is unscoped "
            "and must hold exactly one bucket whatever company is active",
        )
