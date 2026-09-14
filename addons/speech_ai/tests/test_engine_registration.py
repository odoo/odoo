from odoo.libs.documents import TEXT, get_writers
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.speech_ai.tools.writers import AiSpeech, written_by


@tagged("post_install", "-at_install")
class TestEngineRegistration(TransactionCase):
    def _ours(self):
        engines = []
        for mimetype in ("audio/mpeg", "audio/wav", "audio/ogg", "audio/flac"):
            engines += [
                writer
                for writer in get_writers(mimetype, TEXT)
                if isinstance(writer, AiSpeech)
            ]
        return engines

    def test_every_format_registered_is_one_a_vendor_says_it_speaks(self):
        unspoken = [
            engine.mimetype
            for engine in self._ours()
            if not any(
                engine.mimetype in written_by(self.env, vendor)
                for vendor in ("openai", "deepgram", "groq", "gemini")
            )
        ]
        self.assertEqual(
            unspoken,
            [],
            "a writer registered for a format no vendor speaks reports itself "
            "available and then fails at the vendor call",
        )

    def test_a_format_no_vendor_speaks_has_no_engine_at_all(self):
        self.assertEqual(written_by(self.env, "openai") & {"audio/x-aiff"}, frozenset())
        self.assertEqual(
            [w for w in get_writers("audio/x-aiff", TEXT) if isinstance(w, AiSpeech)],
            [],
        )

    def test_flac_is_spoken_by_deepgram_and_not_by_openai(self):
        self.assertIn("audio/flac", written_by(self.env, "deepgram"))
        self.assertNotIn("audio/flac", written_by(self.env, "openai"))
        self.assertTrue(
            [w for w in get_writers("audio/flac", TEXT) if isinstance(w, AiSpeech)]
        )

    def test_the_formats_openai_declares_are_the_ones_it_is_asked_for(self):
        self.assertEqual(
            written_by(self.env, "openai"),
            frozenset({"audio/mpeg", "audio/wav", "audio/ogg"}),
        )

    def test_deepgram_declares_its_own_encodings(self):
        self.assertIn("audio/mpeg", written_by(self.env, "deepgram"))
