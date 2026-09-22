from odoo.http.openapi import RouteInfo
from odoo.tests import TransactionCase, tagged


def route(receiver=None, auth="receiver"):
    routing = {"type": "http", "auth": auth}
    if receiver:
        routing["receiver"] = receiver
    return RouteInfo(
        rule="/hook/<string:code>",
        methods=frozenset({"POST"}),
        routing=routing,
        handler=lambda self, code: None,
    )


@tagged("post_install", "-at_install", "integration")
class TestOpenAPIReceiverSecurity(TransactionCase):
    """What a gated door asks of its caller is on the rows that answer for
    it, so the document reads them instead of stating an open door."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receivers = cls.env["integration.receiver"]
        cls.ir_http = cls.env["ir.http"]

    def _receiver(self, code, **vals):
        return self.receivers.create({"name": code, "code": code, **vals})

    def test_a_route_of_another_auth_is_not_the_resolver_s_business(self):
        self.assertIsNone(self.ir_http._openapi_security_for(route(auth="bearer")))
        self.assertIsNone(self.ir_http._openapi_security_for(route(auth="public")))

    def test_a_receiver_route_naming_no_resolver_states_no_credential(self):
        self.assertEqual(self.ir_http._openapi_security_for(route()), [])

    def test_a_receiver_route_naming_a_model_that_is_gone_states_no_credential(self):
        spec = route(receiver="no.such.model:_receiver_for_x")
        self.assertEqual(self.ir_http._openapi_security_for(spec), [])

    def test_a_door_the_subject_proves_says_the_path_carries_the_proof(self):
        # mail/unfollow and its kind: the receiver model carries no gate, the
        # token in the path is the proof, and an empty `security` would read
        # as an open door.
        resolved = dict(
            self.ir_http._openapi_security_for(
                route(receiver="res.partner:_receiver_for_x")
            )
        )
        self.assertEqual(list(resolved), ["receiverSubject"])
        self.assertEqual(resolved["receiverSubject"]["in"], "path")

    def test_a_door_no_row_answers_for_yet_states_the_scheme_one_would_use(self):
        self.receivers.search([]).unlink()
        resolved = dict(
            self.ir_http._openapi_security_for(
                route(receiver="integration.receiver:_receiver_for_code")
            )
        )
        default = self.receivers._fields["auth_type"].default
        default = default(self.receivers) if callable(default) else default
        self.assertEqual(default, "bearer")
        self.assertEqual(list(resolved), ["receiverBearer"])

    def test_the_document_names_the_schemes_the_rows_use(self):
        self._receiver("openapi_bearer", auth_type="bearer")
        self._receiver("openapi_hmac", auth_type="hmac_sha256")

        resolved = dict(
            self.ir_http._openapi_security_for(
                route(receiver="integration.receiver:_receiver_for_code")
            )
        )

        self.assertIn("receiverBearer", resolved)
        self.assertEqual(resolved["receiverBearer"]["scheme"], "bearer")
        self.assertIn("receiverSha256Signature", resolved)
        signature = resolved["receiverSha256Signature"]
        self.assertEqual(signature["in"], "header")
        self.assertTrue(signature["name"])
        self.assertIn("raw body", signature["description"])

    def test_a_signature_header_every_row_agrees_on_is_the_one_named(self):
        self.receivers.search([("auth_type", "=", "hmac_sha256")]).unlink()
        self._receiver(
            "openapi_stripe",
            auth_type="hmac_sha256",
            signature_header="Stripe-Signature",
        )

        resolved = dict(
            self.ir_http._openapi_security_for(
                route(receiver="integration.receiver:_receiver_for_code")
            )
        )

        self.assertEqual(
            resolved["receiverSha256Signature"]["name"], "Stripe-Signature"
        )

    def test_two_rows_disagreeing_on_the_header_fall_back_to_the_default(self):
        self.receivers.search([("auth_type", "=", "hmac_sha256")]).unlink()
        self._receiver("openapi_a", auth_type="hmac_sha256", signature_header="X-A")
        self._receiver("openapi_b", auth_type="hmac_sha256", signature_header="X-B")

        resolved = dict(
            self.ir_http._openapi_security_for(
                route(receiver="integration.receiver:_receiver_for_code")
            )
        )

        self.assertEqual(
            resolved["receiverSha256Signature"]["name"], "X-Hub-Signature-256"
        )

    def test_a_door_that_admits_without_a_credential_says_which_gate_it_is(self):
        self.receivers.search([]).unlink()
        self._receiver("openapi_open", auth_type="none")

        resolved = dict(
            self.ir_http._openapi_security_for(
                route(receiver="integration.receiver:_receiver_for_code")
            )
        )

        self.assertEqual(list(resolved), ["receiverOpen"])
        self.assertIn("No header is read", resolved["receiverOpen"]["description"])
