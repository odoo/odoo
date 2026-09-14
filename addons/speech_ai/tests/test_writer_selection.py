from unittest.mock import Mock, patch

from odoo.libs.documents import TEXT, get_writers
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools.router import MlRouter
from odoo.addons.speech_ai.tools.writers import AiSpeech


@tagged("post_install", "-at_install")
class TestWriterSelection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for code in ("openai", "deepgram"):
            endpoint = cls.env["integration.service"].search([("code", "=", code)])
            cls.env["credential.credential"].create(
                {
                    "name": code,
                    "endpoint_id": endpoint.id,
                    "api_key": "K",
                    "bearer_token": "K",
                }
            )

    def _writer(self, mimetype):
        return next(
            writer
            for writer in get_writers(mimetype, TEXT)
            if isinstance(writer, AiSpeech)
        )

    def _spoken_by(self, mimetype):
        vendors = []

        def run(model, request_func, **kwargs):
            vendors.append(model.provider_id.code)
            return request_func(Mock(synthesize=Mock(return_value=b"AUDIO")), model)

        with patch.object(MlRouter, "run_with_fallback", side_effect=run):
            self._writer(mimetype).write("hola", env=self.env)
        return vendors

    def test_a_format_only_one_vendor_writes_is_sent_to_that_vendor(self):
        for mimetype in ("audio/flac", "audio/aac"):
            with self.subTest(mimetype=mimetype):
                self.assertEqual(self._spoken_by(mimetype), ["deepgram"])

    def test_a_format_both_vendors_write_goes_to_the_best_ranked(self):
        self.assertEqual(len(self._spoken_by("audio/mpeg")), 1)

    def test_availability_and_selection_agree(self):
        for mimetype in ("audio/mpeg", "audio/flac", "audio/wav"):
            with self.subTest(mimetype=mimetype):
                self.assertTrue(self._writer(mimetype).available(self.env))
