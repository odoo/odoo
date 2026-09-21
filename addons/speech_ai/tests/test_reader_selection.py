from unittest.mock import Mock, patch

from psycopg.errors import IntegrityError

from odoo.exceptions import UserError
from odoo.libs.documents import Document
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.gateway_ml.tools.router import MlRouter
from odoo.addons.speech.tools.engines import engine_error
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

    def test_the_company_vocabulary_and_speaker_separation_reach_the_vendor(self):
        self._allow(self.openai)
        self.env["speech.vocabulary"].create(
            {"name": "Proxity", "company_id": self.env.company.id}
        )

        _cues, client = self._read()

        kwargs = client.transcribe_cues.call_args.kwargs
        self.assertIn("Proxity", kwargs["vocabulary"])
        self.assertTrue(kwargs["speakers"])

    def test_a_vendors_speaker_index_becomes_one_label_for_every_consumer(self):
        self._allow(self.openai)
        spans = [
            {"text": "hola", "end": 1, "speaker": "Speaker 2", "speaker_index": 2},
            {"text": "sí", "start": 1, "end": 2, "speaker": ""},
        ]
        client = Mock(transcribe_cues=Mock(return_value=spans))
        with patch.object(MlRouter, "_get_client", return_value=client):
            cues = AiTranscription().read(
                Document(_OGG, "audio/ogg", "a.ogg", env=self.env)
            )
        self.assertEqual([cue.speaker for cue in cues], ["SPEAKER_2", ""])

    def test_a_recording_larger_than_the_model_takes_is_refused_before_sending(self):
        self._allow(self.openai)
        for xmlid in (
            "gateway_ml.ai_model_openai_whisper_1",
            "gateway_ml.ai_model_openai_gpt_transcribe",
        ):
            self.env.ref(xmlid).write({"max_audio_mb": 1, "fallback_model_ids": [(5,)]})
        big = _OGG + b"\x00" * (1024 * 1024 + 1)
        client = Mock(transcribe_cues=Mock(return_value=[]))
        document = Document(big, "audio/ogg", "long.ogg", env=self.env)
        with (
            patch.object(MlRouter, "_get_client", return_value=client),
            self.assertRaises(UserError) as caught,
        ):
            AiTranscription().read(document)
        self.assertIn("accepts at most", str(caught.exception))
        self.assertTrue(engine_error(document))
        client.transcribe_cues.assert_not_called()


@tagged("post_install", "-at_install")
class TestVocabulary(TransactionCase):
    def test_a_company_hears_its_own_terms_and_the_shared_ones(self):
        other = self.env["res.company"].create({"name": "Other vocabulary company"})
        Vocabulary = self.env["speech.vocabulary"]
        Vocabulary.create({"name": "Mine", "company_id": self.env.company.id})
        Vocabulary.create({"name": "Shared"})
        Vocabulary.create({"name": "Theirs", "company_id": other.id})
        terms = Vocabulary._keyterms(self.env.company)
        self.assertIn("Mine", terms)
        self.assertIn("Shared", terms)
        self.assertNotIn("Theirs", terms)

    def test_a_term_is_registered_once_per_company(self):
        Vocabulary = self.env["speech.vocabulary"]
        Vocabulary.create({"name": "Unico"})
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            Vocabulary.create({"name": "Unico"})


@tagged("post_install", "-at_install")
class TestCanTranscribeFollowsTheAttachmentsCompany(TransactionCase):
    def test_the_attachments_company_policy_decides(self):
        endpoint = self.env["integration.service"].search([("code", "=", "openai")])
        self.env["credential.credential"].create(
            {
                "name": "openai",
                "endpoint_id": endpoint.id,
                "bearer_token": "K",
                "company_id": False,
            }
        )
        other = self.env["res.company"].create({"name": "Other transcription company"})
        self.env["gateway.ml.policy"].create(
            {
                "company_id": other.id,
                "purpose_id": self.env.ref("speech_ai.purpose_speech_transcription").id,
                "provider_ids": [
                    (6, 0, self.env.ref("gateway_ml.ai_provider_openai").ids)
                ],
            }
        )
        Attachment = self.env["ir.attachment"]
        here = Attachment.create(
            {"name": "here.ogg", "raw": _OGG, "company_id": self.env.company.id}
        )
        there = Attachment.create(
            {"name": "there.ogg", "raw": _OGG, "company_id": other.id}
        )
        self.assertFalse(here.can_transcribe)
        self.assertTrue(there.can_transcribe)
