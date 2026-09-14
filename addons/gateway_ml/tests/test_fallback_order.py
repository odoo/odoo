from unittest.mock import patch

from psycopg.errors import IntegrityError

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.gateway_ml.tests.test_model_selection import _SelectionCase
from odoo.addons.gateway_ml.tools.router import MlRouter
from odoo.addons.integration.tools.exceptions import CommError, ServerError


@tagged("post_install", "-at_install")
class TestFallbackOrder(_SelectionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        keyed = cls._provider("order_keyed")
        cls.primary = cls._model(keyed, "order-primary")
        cls.first = cls._model(keyed, "order-z-first")
        cls.second = cls._model(keyed, "order-a-second")

    @mute_logger("odoo.addons.gateway_ml.tools.router")
    def test_the_chain_runs_in_the_order_the_hops_were_given(self):
        self.primary.fallback_ids = [
            Command.create({"fallback_id": self.second.id, "sequence": 20}),
            Command.create({"fallback_id": self.first.id, "sequence": 10}),
        ]
        attempted = []

        def fail(client, ai_model):
            attempted.append(ai_model.code)
            raise ServerError("503")

        with patch.object(MlRouter, "_get_client", return_value=object()):
            with self.assertRaises(CommError):
                MlRouter(self.env).run_with_fallback(self.primary, fail)
        self.assertEqual(
            attempted, ["order-primary", "order-z-first", "order-a-second"]
        )

    def test_writing_the_models_keeps_their_order(self):
        for order in ([self.first, self.second], [self.second, self.first]):
            with self.subTest(order=[m.code for m in order]):
                self.primary.fallback_model_ids = [Command.set([m.id for m in order])]
                self.assertEqual(
                    self.primary.fallback_model_ids.ids, [m.id for m in order]
                )

    def test_a_model_created_with_its_fallbacks_keeps_their_order(self):
        created = self.env["gateway.ml.model"].create(
            {
                "provider_id": self.primary.provider_id.id,
                "name": "order created",
                "code": "order-created",
                "fallback_model_ids": [Command.set([self.second.id, self.first.id])],
            }
        )
        self.assertEqual(
            created.fallback_ids.sorted("sequence").fallback_id.ids,
            [self.second.id, self.first.id],
        )

    def test_a_hop_that_cannot_stand_in_is_refused_when_configured(self):
        audio = self._model(self._provider("order_audio"), "order-audio", kind="audio")
        with self.assertRaises(ValidationError):
            self.primary.fallback_ids = [Command.create({"fallback_id": audio.id})]

    def test_a_hop_is_listed_once(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            self.primary.fallback_ids = [
                Command.create({"fallback_id": self.first.id}),
                Command.create({"fallback_id": self.first.id}),
            ]
            self.env.flush_all()
