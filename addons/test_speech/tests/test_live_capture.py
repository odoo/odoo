import base64
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from .common import SpeechCase, StubTranscription

WAV = base64.b64encode(b"RIFF-not-really-a-wav").decode()


class StubWavTranscription(StubTranscription):
    name = "stub_wav_transcription"
    mimetypes = frozenset({"audio/wav"})


@tagged("post_install", "-at_install")
class TestDictation(SpeechCase):
    def setUp(self):
        super().setUp()
        self.engine = self._register(StubWavTranscription())
        self.writer = new_test_user(
            self.env, "dictating_user", groups="base.group_user"
        )
        self.Dictation = self.env["speech.dictation"].with_user(self.writer)

    def _start(self, **kwargs):
        started = self.Dictation.start_dictation(language="es", **kwargs)
        return self.Dictation.browse(started["id"]), started

    def test_a_dictation_is_a_live_timeline_named_on_its_channel(self):
        dictation, started = self._start(prompt="Proxity, Asanit")
        self.assertTrue(dictation.is_live)
        self.assertEqual(
            started["channel"], f"speech.live/speech.dictation/{dictation.id}"
        )
        self.assertEqual(dictation.user_id, self.writer)

    def test_a_chunk_is_a_live_segment_transcribed_first(self):
        dictation, _started = self._start()
        segment_id = dictation.push_chunk(WAV, 0.0, 6.5)
        segment = self.env["media.segment"].browse(segment_id)
        self.assertTrue(segment.live)
        self.assertEqual((segment.start_ms, segment.end_ms), (0, 6500))
        job = self.env["ir.job"].search(
            [("identity_key", "=", f"speech.transcribe.{segment.attachment_id.id}")]
        )
        self.assertEqual(job.priority, 1)
        self.assertEqual(dictation.live_chunk_count, 1)
        self.assertEqual(dictation.live_elapsed_s, 6.5)

    def test_each_chunk_is_heard_under_the_dictation_purpose(self):
        dictation, _started = self._start(prompt="Proxity, Asanit")
        segment = self.env["media.segment"].browse(dictation.push_chunk(WAV, 0.0, 6.0))
        with patch.object(type(dictation), "_live_publish", autospec=True) as publish:
            segment.attachment_id._transcribe()
        options = self.engine.calls[-1].options
        self.assertEqual(options["purpose"], "speech.transcription.dictation")
        self.assertEqual(options["language"], "es")
        self.assertEqual(options["prompt"], "Proxity, Asanit")
        payload = publish.call_args.args[1]
        self.assertEqual(payload["event"], "chunk")
        self.assertEqual(payload["segment_id"], segment.id)
        self.assertEqual(payload["text"], "the invoice went out\non Tuesday")

    def test_a_chunk_that_fails_is_still_answered(self):
        self.engine.error = RuntimeError("down")
        dictation, _started = self._start()
        segment = self.env["media.segment"].browse(dictation.push_chunk(WAV, 0.0, 6.0))
        with patch.object(type(dictation), "_live_publish", autospec=True) as publish:
            segment.attachment_id._transcribe()
        payload = publish.call_args.args[1]
        self.assertEqual((payload["segment_id"], payload["text"]), (segment.id, ""))
        self.assertIn("down", payload["error"])

    def test_chunks_arriving_after_the_stop_are_still_published(self):
        dictation, _started = self._start()
        segment = self.env["media.segment"].browse(dictation.push_chunk(WAV, 0.0, 6.0))
        dictation.action_stop_live()
        with patch.object(type(dictation), "_live_publish", autospec=True) as publish:
            segment.attachment_id._transcribe()
        self.assertEqual(publish.call_args.args[1]["event"], "chunk")

    def test_no_chunk_outside_a_live_session(self):
        dictation, _started = self._start()
        dictation.action_stop_live()
        with self.assertRaisesRegex(UserError, "live session"):
            dictation.push_chunk(WAV, 0.0, 6.0)

    def test_audio_must_be_base64(self):
        dictation, _started = self._start()
        with self.assertRaises(UserError):
            dictation.push_chunk("%%%", 0.0, 6.0)

    def test_without_an_engine_the_chunk_is_refused(self):
        dictation, _started = self._start()
        self.engine.mimetypes = frozenset()
        with self.assertRaisesRegex(UserError, "No speech engine"):
            dictation.push_chunk(WAV, 0.0, 6.0)

    def test_dictating_into_a_record_needs_to_read_it(self):
        private = self.env["res.partner"].create({"name": "Hidden", "active": True})
        self.env["ir.access"].create(
            {
                "name": "nobody reads Hidden",
                "model_id": self.env.ref("base.model_res_partner").id,
                "group_id": self.env.ref("base.group_everyone").id,
                "kind": "guard",
                "operation": "crud",
                "domain": f"[('id', '!=', {private.id})]",
            }
        )
        with self.assertRaises(AccessError):
            self._start(res_model="res.partner", res_id=private.id)

    def test_a_dictation_is_its_speakers_own(self):
        dictation, _started = self._start()
        other = new_test_user(
            self.env, "other_dictating_user", groups="base.group_user"
        )
        self.assertFalse(
            self.env["speech.dictation"]
            .with_user(other)
            .search([("id", "=", dictation.id)])
        )

    def test_the_live_channel_is_served_to_whoever_reads_the_record(self):
        dictation, started = self._start()
        channel = started["channel"]
        served = (
            self.env["ir.websocket"].with_user(self.writer)._get_bus_channels([channel])
        )
        self.assertIn((dictation, "live"), served)
        other = new_test_user(self.env, "eavesdropper", groups="base.group_user")
        served = self.env["ir.websocket"].with_user(other)._get_bus_channels([channel])
        self.assertNotIn((dictation, "live"), served)

    def test_only_live_timelines_have_a_live_channel(self):
        served = self.env["ir.websocket"]._get_bus_channels(
            [f"speech.live/res.partner/{self.env.user.partner_id.id}"]
        )
        self.assertNotIn((self.env.user.partner_id, "live"), served)
