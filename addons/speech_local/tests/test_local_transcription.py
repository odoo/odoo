import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    BaseReader,
    Cue,
    get_readers,
    register_reader,
    unregister_reader,
)
from odoo.tests import TransactionCase, tagged

from odoo.addons.speech.tools.engines import (
    record_engine_error,
    transcription_engines,
)
from odoo.addons.speech_local.tools import reader as local
from odoo.addons.speech_local.tools.engine import (
    REQUIRED,
    Utterance,
    speaker_of,
    whisper_language,
)

READER = local.__name__


class FakeEngine:
    def __init__(self, cues):
        self.cues = cues
        self.calls = []

    def transcribe(self, samples, language=None):
        self.calls.append((samples, language))
        return list(self.cues)


class VendorStub(BaseReader):
    name = "vendor_stub"
    mimetypes = frozenset({"audio/mpeg"})
    yields = (CUES,)
    cost = EXPENSIVE

    def __init__(self, usable, cues=None, error=None):
        self.usable = usable
        self.cues = cues
        self.error = error

    def available(self, env, purpose=None):
        return self.usable

    def read(self, document):
        if self.error:
            record_engine_error(document, self.error)
            raise self.error
        return self.cues


def _utterance(start, end):
    return Utterance(start, end, np.zeros(0, dtype=np.float32))


@tagged("post_install", "-at_install")
class TestLocalTranscription(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reader = next(
            r
            for r in get_readers("audio/mpeg", CUES)
            if r.name == "local_transcription"
        )
        cls.cues = [Cue(0.0, 2.0, "buenos días", "SPEAKER_0")]

    def setUp(self):
        super().setUp()
        self.models = Path(tempfile.mkdtemp())
        self.addCleanup(local._ENGINES.pop, self.models, None)
        self.env["ir.config_parameter"].sudo().set_param(
            local.MODEL_DIR_PARAM, str(self.models)
        )

    def _complete_models(self):
        for name in REQUIRED:
            (self.models / name).write_bytes(b"")

    def _vendor(self, usable, **answer):
        vendor = VendorStub(usable, **answer)
        register_reader(vendor)
        self.addCleanup(unregister_reader, vendor)
        return vendor

    def _usable_engines(self):
        return [e.name for e in transcription_engines("audio/mpeg", self.env)]

    def _audio(self):
        return self.env["ir.attachment"].create(
            {"name": "call.mp3", "mimetype": "audio/mpeg", "raw": b"fake-audio"}
        )

    def test_unavailable_until_every_required_model_is_there(self):
        self.assertFalse(self.reader.available(self.env))
        (self.models / REQUIRED[0]).write_bytes(b"")
        self.assertFalse(self.reader.available(self.env))
        self._complete_models()
        self.assertTrue(self.reader.available(self.env))

    def test_transcribes_where_no_vendor_serves(self):
        self._complete_models()
        self._vendor(usable=False)
        self.assertEqual(self._usable_engines(), ["local_transcription"])
        engine = FakeEngine(self.cues)
        attachment = self._audio()
        with (
            patch(f"{READER}.local_engine", return_value=engine),
            patch(f"{READER}.decode_audio", return_value=np.zeros(8)),
        ):
            cues, engine_name = attachment._read_transcript(language="es_MX")
        self.assertEqual(cues, self.cues)
        self.assertEqual(engine_name, "local_transcription")
        self.assertEqual(engine.calls[0][1], "es_MX")

    def test_a_vendor_that_answers_is_never_second_guessed(self):
        self._complete_models()
        vendor_cues = [Cue(0.0, 1.0, "from the vendor", "SPEAKER_0")]
        self._vendor(usable=True, cues=vendor_cues)
        engine = FakeEngine(self.cues)
        with patch(f"{READER}.local_engine", return_value=engine):
            cues, engine_name = self._audio()._read_transcript()
        self.assertEqual((cues, engine_name), (vendor_cues, "vendor_stub"))
        self.assertFalse(engine.calls)

    def test_a_vendor_that_fails_is_covered_by_the_local_engine(self):
        self._complete_models()
        self._vendor(usable=True, error=RuntimeError("vendor down"))
        attachment = self._audio()
        with (
            patch(f"{READER}.local_engine", return_value=FakeEngine(self.cues)),
            patch(f"{READER}.decode_audio", return_value=np.zeros(8)),
        ):
            attachment._transcribe()
        self.assertEqual(attachment.transcript_state, "done")
        self.assertEqual(attachment.transcript_engine, "local_transcription")
        self.assertFalse(attachment.transcript_error)

    def test_it_is_offered_after_its_peers_whenever_it_registered(self):
        vendor = self._vendor(usable=True)
        names = [r.name for r in get_readers("audio/mpeg", CUES)]
        self.assertGreater(names.index("local_transcription"), names.index(vendor.name))

    def test_an_engine_failure_is_reported_on_the_document(self):
        self._complete_models()

        class Broken(FakeEngine):
            def transcribe(self, samples, language=None):
                raise RuntimeError("model crashed")

        attachment = self._audio()
        with (
            patch(f"{READER}.local_engine", return_value=Broken([])),
            patch(f"{READER}.decode_audio", return_value=np.zeros(8)),
        ):
            attachment._transcribe()
        self.assertEqual(attachment.transcript_state, "failed")
        self.assertIn("model crashed", attachment.transcript_error)

    def test_the_voice_heard_longest_names_the_utterance(self):
        turns = [(0.0, 1.0, 0), (1.0, 4.0, 1), (4.0, 5.0, 0)]
        self.assertEqual(speaker_of(_utterance(0.5, 4.5), turns), "SPEAKER_1")
        self.assertEqual(speaker_of(_utterance(6.0, 7.0), turns), "")
        self.assertEqual(speaker_of(_utterance(0.0, 1.0), []), "")

    def test_whisper_takes_the_bare_language_code(self):
        self.assertEqual(whisper_language("es_MX"), "es")
        self.assertEqual(whisper_language("en-US"), "en")
        self.assertEqual(whisper_language(None), "")
