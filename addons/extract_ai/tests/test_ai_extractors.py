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
        client.complete.return_value = answer

        orchestrator = MagicMock()
        orchestrator.select_model.return_value = MagicMock(code="a-model")
        orchestrator.run.side_effect = lambda operation, request, model=None, **kw: (
            MlResult(
                model, **MlRouter(self.env)._dispatch(operation, request, client, model)
            )
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
        self.assertEqual(client.complete.call_args.kwargs["images"], ())
        sent = client.complete.call_args
        self.assertIn("CONSUMO 100 KWH", sent.args[0])
        self.assertIn("total", sent.kwargs["response_schema"]["properties"])
        self.assertIn("Never invent a value", sent.kwargs["system"])

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

        (image,) = client.complete.call_args.kwargs["images"]
        self.assertEqual(image[1], "image/png")

    def test_only_the_missing_fields_are_asked_about(self):
        orchestrator, client = self._orchestrator()

        self._run(self.text_reader, _TEXT_DOC, orchestrator, wanted=("total",))

        sent = client.complete.call_args
        self.assertEqual(list(sent.kwargs["response_schema"]["properties"]), ["total"])
        self.assertNotIn("vendor_vat", sent.args[0])

    def test_the_purpose_names_the_document_type(self):
        orchestrator, _ = self._orchestrator()

        self._run(self.text_reader, _TEXT_DOC, orchestrator, doc_type="receipt")

        self.assertEqual(
            orchestrator.select_model.call_args.kwargs["purpose"], "extract.receipt"
        )
        self.assertEqual(orchestrator.run.call_args.args[1].purpose, "extract.receipt")

    def test_the_company_is_the_environments_by_default(self):
        orchestrator, _ = self._orchestrator()

        self._run(self.text_reader, _TEXT_DOC, orchestrator)

        self.assertEqual(
            orchestrator.select_model.call_args.kwargs["company_id"],
            self.env.company.id,
        )
        self.assertEqual(
            orchestrator.run.call_args.kwargs["company_id"], self.env.company.id
        )

    def test_a_company_named_by_the_source_is_the_one_asked(self):
        other = self.env["res.company"].create({"name": "Other extract company"})
        source = Document(
            b"CONSUMO 100 KWH TOTAL 139.86", "text/plain", "bill.txt", company=other
        )
        orchestrator, _ = self._orchestrator()

        self._run(self.text_reader, source, orchestrator)

        self.assertEqual(
            orchestrator.select_model.call_args.kwargs["company_id"], other.id
        )
        self.assertEqual(orchestrator.run.call_args.kwargs["company_id"], other.id)

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
        client.complete.assert_not_called()

    def test_a_vendor_failure_is_not_raised_at_the_cascade(self):
        orchestrator, _ = self._orchestrator()
        orchestrator.run.side_effect = RuntimeError("all keys down")

        self.assertIsNone(self._run(self.text_reader, _TEXT_DOC, orchestrator))

    def test_an_unparseable_answer_is_not_raised_either(self):
        orchestrator, _ = self._orchestrator(answer="I think the total is about 140")

        self.assertIsNone(self._run(self.text_reader, _TEXT_DOC, orchestrator))

    def test_the_schema_chooses_the_optimization_and_the_purpose(self):
        from odoo.addons.extract.tools import schema as schema_mod

        name = "test_declared_for_ai"
        schema_mod.register_schema(
            name,
            {"total": schema_mod.FieldSpec("float")},
            optimize_for="accuracy",
            purpose="test.reading",
        )
        self.addCleanup(schema_mod._SCHEMAS.pop, name, None)
        orchestrator, _ = self._orchestrator()

        self._run(self.text_reader, _TEXT_DOC, orchestrator, doc_type=name)

        chosen = orchestrator.select_model.call_args.kwargs
        self.assertEqual(chosen["optimize_for"], "accuracy")
        self.assertEqual(chosen["purpose"], "test.reading")
        self.assertEqual(orchestrator.run.call_args.args[1].purpose, "test.reading")
