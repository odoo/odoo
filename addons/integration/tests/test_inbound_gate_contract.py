from unittest.mock import patch

from werkzeug.routing import Map, Rule

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "integration")
class TestInboundGateContract(TransactionCase):
    """What a caller must send is on the gate's own form, derived from the
    gate rather than written twice."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receivers = cls.env["integration.receiver"]

    def _receiver(self, code, **vals):
        return self.receivers.create({"name": code, "code": code, **vals})

    def test_a_bearer_gate_names_both_headers_a_caller_may_use(self):
        gate = self._receiver("contract_bearer", auth_type="bearer")

        self.assertIn("Authorization: Bearer", gate.contract_scheme)
        self.assertIn("X-Device-Token", gate.contract_scheme)

    def test_a_signed_gate_names_its_header_digest_and_prefix(self):
        gate = self._receiver(
            "contract_signed",
            auth_type="hmac_sha512",
            signature_header="X-Partner-Signature",
            signature_prefix="sha512=",
        )

        self.assertIn("X-Partner-Signature: sha512=", gate.contract_scheme)
        self.assertIn("SHA512 of the raw body", gate.contract_scheme)

    def test_a_timestamped_gate_states_how_old_a_call_may_be(self):
        gate = self._receiver(
            "contract_timestamped",
            auth_type="bearer",
            timestamp_verification_enabled=True,
            timestamp_header="X-When",
            timestamp_max_age_seconds=120,
        )

        self.assertIn("X-When", gate.contract_scheme)
        self.assertIn("120s", gate.contract_scheme)

    def test_an_open_gate_says_what_admits_the_caller_instead(self):
        gate = self._receiver("contract_open", auth_type="none")

        self.assertIn("No credential", gate.contract_scheme)
        self.assertIn("address allow-list", gate.contract_scheme)

    def test_the_caps_are_the_gate_s_own_numbers(self):
        gate = self._receiver(
            "contract_capped",
            auth_type="bearer",
            max_payload_size=2048,
            rate_limit_enabled=True,
            rate_limit_requests=30,
            rate_limit_window_seconds=15,
            ip_whitelist="10.0.0.1, 192.168.0.0/24",
        )

        limits = gate.contract_limits
        self.assertIn("2048 bytes", limits)
        self.assertIn("30 calls per 15s", limits)
        self.assertIn("10.0.0.1, 192.168.0.0/24", limits)

    def test_a_cap_that_is_off_is_not_promised(self):
        gate = self._receiver(
            "contract_uncapped",
            auth_type="bearer",
            rate_limit_enabled=False,
            ip_whitelist="",
        )

        self.assertNotIn("calls per", gate.contract_limits)
        self.assertNotIn("Called from", gate.contract_limits)

    def test_the_routes_are_read_from_the_routing_map(self):
        def endpoint(routing):
            def handler():
                return None

            handler.routing = routing
            return handler

        routing_map = Map(
            [
                Rule(
                    "/hook/<int:ident>",
                    endpoint=endpoint({"receiver": "res.partner:_hook_subject"}),
                    methods=["POST"],
                ),
                Rule(
                    "/hook/<int:ident>/state",
                    endpoint=endpoint({"receiver": "res.partner:_hook_subject"}),
                    methods=["GET"],
                ),
                Rule(
                    "/gate/<string:code>",
                    endpoint=endpoint({"receiver": "integration.receiver:code"}),
                ),
                Rule(
                    "/page",
                    endpoint=endpoint({"auth": "user"}),
                    methods=["GET"],
                ),
            ]
        )
        with patch.object(
            type(self.env["ir.http"]), "routing_map", return_value=routing_map
        ):
            routes = self.receivers._inbound_routes_by_model()

        self.assertEqual(
            routes,
            {
                "res.partner": [
                    "POST /hook/<int:ident>",
                    "GET /hook/<int:ident>/state",
                ],
                "integration.receiver": ["GET, POST /gate/<string:code>"],
            },
        )

    def test_every_model_a_receiver_route_names_is_a_model(self):
        for model_name, rules in self.receivers._inbound_routes_by_model().items():
            self.assertIn(model_name, self.env, f"{model_name} is not a model")
            for rule in rules:
                methods, _, path = rule.rpartition(" ")
                self.assertTrue(methods and path.startswith("/"), rule)

    def test_a_gate_that_answers_for_a_record_claims_that_record_s_routes(self):
        gate = self._receiver("contract_record", auth_type="bearer")
        gate.write({"res_model": "res.partner", "res_id": self.env.user.partner_id.id})

        self.assertEqual(
            gate._contract_models(), ["integration.receiver", "res.partner"]
        )
        routes = {"res.partner": ["POST /hook/<int:ident>"]}
        self.assertEqual(gate._contract_routes(routes), ["POST /hook/<int:ident>"])

    def test_the_last_call_is_the_body_the_log_kept(self):
        gate = self._receiver("contract_called", auth_type="bearer")
        self.env["integration.exchange"].create(
            {
                "direction": "inbound",
                "channel_id": f"integration.receiver,{gate.id}",
                "event_type": "probe",
                "request_method": "PUT",
                "request_payload": '{"weight": 12.5}',
                "state": "success",
            }
        )
        gate.invalidate_recordset()

        self.assertIn('{"weight": 12.5}', gate.contract_last_call)
        self.assertIn("PUT", gate.contract_last_call)

    def test_a_gate_nobody_has_called_promises_no_example(self):
        gate = self._receiver("contract_silent", auth_type="bearer")

        self.assertFalse(gate.contract_last_call)
