from odoo.tests.common import TransactionCase

from ..controllers.inbound_controller import InboundController


class TestInboundControllerIdentifierField(TransactionCase):
    def setUp(self):
        super().setUp()
        self.controller = InboundController()

    def test_every_model_resolves_to_identifier(self):
        for model in ("remote.device", "webhook.subscription", "some.other.model", ""):
            with self.subTest(model=model):
                self.assertEqual(
                    self.controller._get_identifier_field(model), "identifier"
                )

    def test_a_subclass_may_name_its_own_field(self):
        class OtherIdentifier(InboundController):
            def _get_identifier_field(self, endpoint_model):
                if endpoint_model == "some.other.model":
                    return "serial"
                return super()._get_identifier_field(endpoint_model)

        controller = OtherIdentifier()
        self.assertEqual(controller._get_identifier_field("some.other.model"), "serial")
        self.assertEqual(
            controller._get_identifier_field("remote.device"), "identifier"
        )
