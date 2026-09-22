from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    TEXT,
    BaseReader,
    BaseWriter,
    Cue,
    get_writers,
    register_reader,
    register_writer,
    unregister_reader,
    unregister_writer,
)
from odoo.tests.common import TransactionCase

from odoo.addons.speech.tools.engines import record_engine_error

SPOKEN = frozenset({"audio/mpeg", "audio/webm", "video/mp4"})

CUE_FIXTURE = [
    Cue(0.0, 1.5, "the invoice went out", ""),
    Cue(1.5, 3.0, "on Tuesday", "Alice"),
]


class StubTranscription(BaseReader):
    name = "stub_transcription"
    mimetypes = SPOKEN
    yields = (CUES,)
    cost = EXPENSIVE

    def __init__(self, cues=None, error=None):
        self.cues = CUE_FIXTURE if cues is None else cues
        self.error = error
        self.calls = []

    def read(self, document):
        self.calls.append(document)
        if self.error:
            record_engine_error(document, self.error)
            raise self.error
        return list(self.cues)


class PurposeAwareTranscription(StubTranscription):
    name = "stub_purpose_aware_transcription"

    def __init__(self, serves=(), cues=None):
        super().__init__(cues=cues)
        self.serves = set(serves)
        self.asked = []

    def available(self, env, purpose=None):
        self.asked.append(purpose)
        return purpose in self.serves


class StubSpeech(BaseWriter):
    name = "stub_speech"
    mimetype = "audio/mpeg"
    consumes = TEXT

    def __init__(self, audio=b"ID3-stub-audio"):
        self.audio = audio
        self.spoken = []

    def write(self, value, **options):
        self.spoken.append((value, options))
        return self.audio


class SpeechCase(TransactionCase):
    def _register(self, engine):
        if isinstance(engine, BaseReader):
            register_reader(engine)
            self.addCleanup(unregister_reader, engine)
            return engine
        # A writer has no cost and `Document.of` takes the first that claims the
        # mimetype, so a stub cannot simply be added beside a real engine the
        # way a reader can: whichever module registered first would answer.
        displaced = get_writers(engine.mimetype, engine.consumes)
        for other in displaced:
            unregister_writer(other)
        register_writer(engine)
        self.addCleanup(self._restore_writers, engine, displaced)
        return engine

    def _restore_writers(self, engine, displaced):
        unregister_writer(engine)
        for other in displaced:
            register_writer(other)

    def _only_writers(self, *engines):
        """Register these writers, in this order, and no others."""
        displaced = get_writers(engines[0].mimetype, engines[0].consumes)
        for other in displaced:
            unregister_writer(other)
        for engine in engines:
            register_writer(engine)
        self.addCleanup(self._restore_only_writers, engines, displaced)
        return engines

    def _restore_only_writers(self, engines, displaced):
        for engine in engines:
            unregister_writer(engine)
        for other in displaced:
            register_writer(other)

    def _audio(self, name="call.mp3", mimetype="audio/mpeg", raw=b"fake-audio"):
        return self.env["ir.attachment"].create(
            {"name": name, "mimetype": mimetype, "raw": raw}
        )

    def _recording(self, name="recording"):
        return self.env["speech.test.recording"].create({"name": name})
