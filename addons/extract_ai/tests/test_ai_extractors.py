from unittest.mock import MagicMock, patch

from odoo.libs.documents import Document
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.extract.tools import GENERATIVE, known_schemas
from odoo.addons.extract_ai.models.ai_extractors import (
    LlmTextExtractor,
    LlmVisionExtractor,
    _media_type,
)
from odoo.addons.gateway_ml.tools import MlResult, MlRouter

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_TEXT_DOC = Document(b"CONSUMO 100 KWH TOTAL 139.86", "text/plain", "bill.txt")
_IMAGE_DOC = Document(_PNG, "image/png", "scan.png")


@tagged("post_install", "-at_install")
class TestAiExtractors(TransactionCase):
    def setUp(self):
        super().setUp()
        self.text_reader = LlmTextExtractor()
        self.vision_reader = LlmVisionExtractor()

    def _orchestrator(self, answer='{"total": 139.86}'):
        client = MagicMock()
        client.simple_completion.return_value = answer
        client.vision_completion.return_value = answer

        orchestrator = MagicMock()
        orchestrator.select_model.return_value = MagicMock(code="a-model")
        orchestrator.run.side_effect = lambda operation, request, model=None, **kw: (
            MlResult(model, **MlRouter._dispatch(operation, request, client, model))
        )
        return orchestrator, client

    def _run(self, reader, source, orchestrator, doc_type="invoice", wanted=()):
        with patch(
            "odoo.addons.extract_ai.models.ai_extractors.get_router",
            return_value=orchestrator,
        ):
            return reader.extract(source, doc_type, wanted, env=self.env)

    def test_a_document_with_text_does_not_need_a_vision_model(self):
        self.assertTrue(self.text_reader.applies_to(_TEXT_DOC, "invoice"))
        self.assertFalse(self.vision_reader.applies_to(_TEXT_DOC, "invoice"))

    def test_a_scan_reaches_the_vision_reader(self):
        self.assertTrue(self.vision_reader.applies_to(_IMAGE_DOC, "invoice"))

    def test_both_are_the_most_expensive_thing_the_cascade_can_do(self):
        self.assertEqual(self.text_reader.cost, GENERATIVE)
        self.assertEqual(self.vision_reader.cost, GENERATIVE)

    def test_they_can_read_any_registered_document_type(self):
        self.assertEqual(set(self.text_reader.doc_types), set(known_schemas()))
        self.assertIn("receipt", self.vision_reader.doc_types)

    def test_the_text_reader_sends_the_document_and_no_picture(self):
        orchestrator, client = self._orchestrator()

        result = self._run(self.text_reader, _TEXT_DOC, orchestrator)

        self.assertEqual(result, {"total": 139.86})
        client.vision_completion.assert_not_called()
        sent = client.simple_completion.call_args.args[0]
        self.assertIn("CONSUMO 100 KWH", sent)
        self.assertIn("Expected JSON structure", sent)

    def test_the_text_reader_asks_for_no_vision_capability(self):
        orchestrator, _ = self._orchestrator()

        self._run(self.text_reader, _TEXT_DOC, orchestrator)

        self.assertIsNone(
            orchestrator.select_model.call_args.kwargs.get("required_capabilities")
        )

    def test_each_reader_asks_for_the_kind_of_model_it_calls(self):
        for reader, doc, kinds in (
            (self.text_reader, _TEXT_DOC, "chat"),
            (self.vision_reader, _IMAGE_DOC, ("chat", "vision")),
        ):
            with self.subTest(reader=reader.name):
                orchestrator, _ = self._orchestrator()
                self._run(reader, doc, orchestrator)
                self.assertEqual(orchestrator.select_model.call_args.args, (kinds,))

    def test_the_vision_reader_demands_a_model_that_can_see(self):
        orchestrator, _ = self._orchestrator()

        self._run(self.vision_reader, _IMAGE_DOC, orchestrator)

        self.assertEqual(
            orchestrator.select_model.call_args.kwargs["required_capabilities"],
            {"has_vision": True},
        )

    def test_the_image_is_labelled_by_looking_at_it(self):
        orchestrator, client = self._orchestrator()

        self._run(self.vision_reader, _IMAGE_DOC, orchestrator)

        self.assertEqual(
            client.vision_completion.call_args.kwargs["media_type"], "image/png"
        )

    def test_only_the_missing_fields_are_asked_about(self):
        orchestrator, client = self._orchestrator()

        self._run(self.text_reader, _TEXT_DOC, orchestrator, wanted=("total",))

        sent = client.simple_completion.call_args.args[0]
        self.assertIn("total", sent)
        self.assertNotIn("vendor_vat", sent)

    def test_the_media_type_is_read_from_the_bytes(self):
        self.assertEqual(_media_type(_PNG), "image/png")
        self.assertEqual(_media_type(b"\xff\xd8\xff\xe0rest"), "image/jpeg")
        self.assertEqual(_media_type(b"GIF89a rest"), "image/gif")
        with self.assertRaises(ValueError):
            _media_type(b"%PDF-1.7 not an image")

    def test_without_an_environment_it_declines(self):
        self.assertIsNone(self.text_reader.extract(_TEXT_DOC, "invoice", (), env=None))

    def test_with_no_model_configured_it_declines(self):
        orchestrator, client = self._orchestrator()
        orchestrator.select_model.return_value = None

        result = self._run(self.text_reader, _TEXT_DOC, orchestrator)

        self.assertIsNone(result)
        client.simple_completion.assert_not_called()

    def test_a_vendor_failure_is_not_raised_at_the_cascade(self):
        orchestrator, _ = self._orchestrator()
        orchestrator.run.side_effect = RuntimeError("all keys down")

        self.assertIsNone(self._run(self.text_reader, _TEXT_DOC, orchestrator))

    def test_an_unparseable_answer_is_not_raised_either(self):
        orchestrator, _ = self._orchestrator(answer="I think the total is about 140")

        self.assertIsNone(self._run(self.text_reader, _TEXT_DOC, orchestrator))
