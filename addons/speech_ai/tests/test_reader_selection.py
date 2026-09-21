from unittest.mock import Mock, patch

from odoo.libs.documents import Document
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools.router import MlRouter
from odoo.addons.speech_ai.tools.readers import AiTranscription, _pick_timed_model
from odoo.addons.speech_ai.tools.selection import TRANSCRIPTION_PURPOSE

_OGG = b"OggS" + b"\x00" * 64


@tagged("post_install", "-at_install")
class TestReaderSelection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        endpoint = cls.env["integration.service"].search([("code", "=", "openai")])
        cls.env["credential.credential"].create(
            {"name": "openai", "endpoint_id": endpoint.id, "bearer_token": "K"}
        )
        cls.openai = cls.env.ref("gateway_ml.ai_provider_openai")
        cls.transcription = cls.env.ref("speech_ai.purpose_speech_transcription")

    def _allow(self, *providers, company=None):
        return self.env["gateway.ml.policy"].create(
            {
                "company_id": (company or self.env.company).id,
                "purpose_id": self.transcription.id,
                "provider_ids": [(6, 0, [p.id for p in providers])],
            }
        )

    def _pick(self, purpose=TRANSCRIPTION_PURPOSE):
        return _pick_timed_model(self.env, self.env.company.id, purpose)

    def _read(self, **options):
        client = Mock(transcribe_cues=Mock(return_value=[{"text": "hola", "end": 1}]))
        with patch.object(MlRouter, "_get_client", return_value=client):
            cues = AiTranscription().read(
                Document(_OGG, "audio/ogg", "a.ogg", env=self.env, **options)
            )
        return cues, client

    def test_a_cheaper_model_without_timestamps_is_not_picked_for_cues(self):
        self._allow(self.openai)
        transcribe = self.env.ref("gateway_ml.ai_model_openai_gpt_transcribe")
        whisper = self.env.ref("gateway_ml.ai_model_openai_whisper_1")
        self.assertLess(transcribe.cost_per_audio_minute, whisper.cost_per_audio_minute)
        self.assertEqual(self._pick(), whisper)

    def test_transcription_is_declared_sensitive(self):
        self.assertEqual(self.transcription.key, TRANSCRIPTION_PURPOSE)
        self.assertTrue(self.transcription.sensitive)

    def test_without_a_policy_no_vendor_hears_a_recording(self):
        self.assertFalse(self._pick())
        self.assertFalse(AiTranscription().available(self.env))

        cues, client = self._read()

        self.assertEqual(cues, [])
        client.transcribe_cues.assert_not_called()

    def test_a_policy_naming_another_vendor_keeps_the_recording_home(self):
        self._allow(self.env.ref("gateway_ml.ai_provider_deepgram"))
        self.assertFalse(self._pick())

    def test_a_policy_naming_the_vendor_lets_the_reader_transcribe(self):
        self._allow(self.openai)
        self.assertTrue(AiTranscription().available(self.env))

        cues, client = self._read()

        self.assertEqual([cue.text for cue in cues], ["hola"])
        client.transcribe_cues.assert_called_once()

    def test_the_transcription_policy_governs_a_narrower_purpose(self):
        self._allow(self.openai)

        cues, _client = self._read(purpose="speech.transcription.call")

        self.assertEqual([cue.text for cue in cues], ["hola"])

    def test_the_company_the_document_names_is_the_one_whose_policy_applies(self):
        self._allow(self.openai)
        other = self.env["res.company"].create({"name": "Other speech company"})

        cues, client = self._read(company=other)

        self.assertEqual(cues, [])
        client.transcribe_cues.assert_not_called()
