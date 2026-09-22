from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.libs.documents import CHEAP, Cue
from odoo.tests import tagged

from .common import (
    CUE_FIXTURE,
    PurposeAwareTranscription,
    SpeechCase,
    StubSpeech,
    StubTranscription,
)


@tagged("post_install", "-at_install")
class TestTranscription(SpeechCase):
    def test_nothing_is_transcribable_without_an_engine(self):
        self.assertFalse(self._audio().can_transcribe)

    def test_an_engine_makes_a_recording_transcribable(self):
        self._register(StubTranscription())
        self.assertTrue(self._audio().can_transcribe)

    def test_an_engine_cheaper_than_a_network_call_is_still_an_engine(self):
        engine = StubTranscription()
        engine.cost = CHEAP
        self._register(engine)
        attachment = self._audio()
        self.assertTrue(attachment.can_transcribe)
        attachment._transcribe()
        self.assertEqual(attachment.transcript_state, "done")

    def test_a_container_naming_its_codec_is_still_that_container(self):
        self._register(StubTranscription())
        recorded = self.env["ir.attachment"].create(
            {
                "name": "call.webm",
                "mimetype": "audio/webm;codecs=opus",
                "raw": b"chunk",
            }
        )
        self.assertTrue(recorded.can_transcribe)

    def test_a_spreadsheet_is_not_transcribable_even_with_an_engine(self):
        self._register(StubTranscription())
        sheet = self.env["ir.attachment"].create(
            {"name": "book.csv", "mimetype": "text/csv", "raw": b"a,b"}
        )
        self.assertFalse(sheet.can_transcribe)

    def test_transcribing_stores_the_words_and_their_timing(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment._transcribe()
        self.assertEqual(attachment.transcript_state, "done")
        self.assertEqual(len(attachment.transcript_cues), 2)
        self.assertEqual(attachment.transcript_cues[1]["speaker"], "Alice")
        self.assertEqual(attachment.transcript_text, "the invoice went out\non Tuesday")

    def test_a_transcript_becomes_what_the_attachment_is_indexed_by(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment._transcribe()
        self.assertEqual(attachment.index_content, "the invoice went out\non Tuesday")

    def test_a_transcribed_recording_is_found_by_searching_its_words(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment._transcribe()
        found = self.env["ir.attachment"].search(
            [("id", "=", attachment.id), ("index_content", "ilike", "Tuesday")]
        )
        self.assertEqual(found, attachment)

    def test_the_engine_that_answered_is_recorded(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment._transcribe()
        self.assertEqual(attachment.transcript_engine, "stub_transcription")

    def test_the_engine_is_handed_the_language_that_was_asked_for(self):
        engine = self._register(StubTranscription())
        self._audio()._transcribe(language="es")
        self.assertEqual(engine.calls[0].options["language"], "es")

    def test_the_engine_is_handed_an_environment(self):
        engine = self._register(StubTranscription())
        self._audio()._transcribe()
        self.assertIsNotNone(engine.calls[0].options["env"])

    def test_a_failing_engine_leaves_the_reason_on_the_record(self):
        self._register(StubTranscription(error=ValueError("vendor said no")))
        attachment = self._audio()
        self.assertIsNone(attachment._transcribe())
        self.assertEqual(attachment.transcript_state, "failed")
        self.assertIn("vendor said no", attachment.transcript_error)

    def test_an_engine_outage_is_not_reported_as_a_silent_recording(self):
        self._register(StubTranscription(error=ValueError("vendor is down")))
        attachment = self._audio()
        attachment._transcribe()
        self.assertNotEqual(attachment.transcript_state, "done")
        self.assertFalse(attachment.transcript_cues)

    def test_a_recording_with_nothing_said_is_transcribed_and_empty(self):
        self._register(StubTranscription(cues=[]))
        attachment = self._audio()
        attachment._transcribe()
        self.assertEqual(attachment.transcript_state, "done")
        self.assertEqual(attachment.transcript_text, "")

    def test_transcribing_what_no_engine_reads_is_refused_by_name(self):
        attachment = self._audio()
        with self.assertRaises(UserError):
            attachment._transcribe()

    def test_the_action_refuses_a_selection_it_cannot_read(self):
        with self.assertRaises(UserError):
            self._audio().action_transcribe()

    def test_the_action_queues_a_job_rather_than_calling_the_engine(self):
        engine = self._register(StubTranscription())
        attachment = self._audio()
        attachment.action_transcribe()
        self.assertEqual(attachment.transcript_state, "queued")
        self.assertEqual(engine.calls, [])

    def test_the_queued_job_names_the_method_that_transcribes(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment.action_transcribe()
        job = self.env["ir.job"].search(
            [
                ("model_name", "=", "ir.attachment"),
                ("method_name", "=", "_job_transcribe"),
            ]
        )
        self.assertTrue(job, "the action queued nothing a worker could find")
        self.assertIn(attachment.id, job[0].record_ids)
        self.assertEqual(job[0].channel, "speech")

    def test_running_the_queued_job_transcribes_the_recording(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment.action_transcribe()
        job = self.env["ir.job"].search(
            [
                ("model_name", "=", "ir.attachment"),
                ("method_name", "=", "_job_transcribe"),
            ],
            limit=1,
        )
        target = self.env[job.model_name].browse(job.record_ids)
        getattr(target, job.method_name)(**(job.kwargs or {}))
        self.assertEqual(attachment.transcript_state, "done")
        self.assertEqual(attachment.transcript_text, "the invoice went out\non Tuesday")

    def test_queueing_the_same_recording_twice_does_not_queue_it_twice(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment.action_transcribe()
        attachment.action_transcribe()
        jobs = self.env["ir.job"].search(
            [
                ("model_name", "=", "ir.attachment"),
                ("method_name", "=", "_job_transcribe"),
            ]
        )
        self.assertEqual(len(jobs), 1, "the identity key did not deduplicate")

    def test_a_transcript_is_written_back_as_webvtt(self):
        self._register(StubTranscription())
        attachment = self._audio()
        attachment._transcribe()
        vtt = attachment._transcript_vtt()
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:01.500 --> 00:00:03.000", vtt)
        self.assertIn("<v Alice>on Tuesday", vtt)

    def test_a_recording_carrying_subtitles_is_read_by_the_free_reader(self):
        engine = self._register(StubTranscription())
        subtitles = self.env["ir.attachment"].create(
            {
                "name": "film.vtt",
                "mimetype": "text/vtt",
                "raw": b"WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nalready written\n",
            }
        )
        self.assertFalse(subtitles.can_transcribe)
        self.assertEqual(engine.calls, [])


@tagged("post_install", "-at_install")
class TestTimeline(SpeechCase):
    def test_a_timeline_lasts_as_long_as_its_last_segment_ends(self):
        recording = self._recording()
        recording._add_media_segment(self._audio("a.mp3"), 0, 2000)
        recording._add_media_segment(self._audio("b.mp3"), 2000, 5000)
        self.assertEqual(recording.media_duration_ms, 5000)
        self.assertTrue(recording.has_media)

    def test_an_owner_with_no_media_has_no_duration(self):
        recording = self._recording()
        self.assertEqual(recording.media_duration_ms, 0)
        self.assertFalse(recording.has_media)
        self.assertEqual(recording.timeline_transcript_state, "none")

    def test_the_transcript_is_its_segments_in_order(self):
        self._register(StubTranscription())
        recording = self._recording()
        late = self._audio("b.mp3")
        early = self._audio("a.mp3")
        recording._add_media_segment(late, 2000, 4000)
        recording._add_media_segment(early, 0, 2000)
        early._transcribe()
        late._transcribe()
        self.assertEqual(
            recording.timeline_transcript,
            "the invoice went out\non Tuesday\nthe invoice went out\non Tuesday",
        )

    def test_one_untranscribed_segment_keeps_the_whole_pending(self):
        self._register(StubTranscription())
        recording = self._recording()
        first = self._audio("a.mp3")
        recording._add_media_segment(first, 0, 2000)
        recording._add_media_segment(self._audio("b.mp3"), 2000, 4000)
        first._transcribe()
        self.assertEqual(recording.timeline_transcript_state, "none")

    def test_a_failed_segment_shows_over_a_done_one(self):
        recording = self._recording()
        good = self._audio("a.mp3")
        bad = self._audio("b.mp3")
        recording._add_media_segment(good, 0, 2000)
        recording._add_media_segment(bad, 2000, 4000)
        good.sudo().transcript_state = "done"
        bad.sudo().transcript_state = "failed"
        self.assertEqual(recording.timeline_transcript_state, "failed")

    def test_the_owner_is_told_when_a_segment_is_transcribed(self):
        self._register(StubTranscription())
        recording = self._recording()
        attachment = self._audio()
        recording._add_media_segment(attachment, 0, 2000)
        attachment._transcribe()
        self.assertEqual(recording.transcribed_count, 1)
        self.assertTrue(recording.completed)

    def test_the_owner_is_told_when_a_segment_fails(self):
        self._register(StubTranscription(error=ValueError("no")))
        recording = self._recording()
        attachment = self._audio()
        recording._add_media_segment(attachment, 0, 2000)
        attachment._transcribe()
        self.assertEqual(recording.failed_count, 1)
        self.assertFalse(recording.completed)

    def test_the_owner_is_told_it_is_complete_only_once_every_segment_is(self):
        self._register(StubTranscription())
        recording = self._recording()
        first = self._audio("a.mp3")
        second = self._audio("b.mp3")
        recording._add_media_segment(first, 0, 2000)
        recording._add_media_segment(second, 2000, 4000)
        first._transcribe()
        self.assertFalse(recording.completed)
        second._transcribe()
        self.assertTrue(recording.completed)

    def test_transcribing_a_timeline_queues_every_readable_segment(self):
        self._register(StubTranscription())
        recording = self._recording()
        recording._add_media_segment(self._audio("a.mp3"), 0, 2000)
        recording._add_media_segment(self._audio("b.mp3"), 2000, 4000)
        recording.action_transcribe_media()
        self.assertEqual(
            set(recording.segment_ids.attachment_id.mapped("transcript_state")),
            {"queued"},
        )


@tagged("post_install", "-at_install")
class TestSynthesis(SpeechCase):
    def test_speaking_without_an_engine_is_refused_rather_than_writing_text(self):
        with self.assertRaises(UserError):
            self.env["ir.attachment"]._speech_synthesize("read this aloud")

    def test_speaking_nothing_is_refused(self):
        self._register(StubSpeech())
        with self.assertRaises(UserError):
            self.env["ir.attachment"]._speech_synthesize("   ")

    def test_speaking_stores_the_audio_the_engine_returned(self):
        self._register(StubSpeech())
        attachment = self.env["ir.attachment"]._speech_synthesize("read this aloud")
        self.assertEqual(attachment.raw, b"ID3-stub-audio")
        self.assertEqual(attachment.mimetype, "audio/mpeg")
        self.assertTrue(attachment.name.endswith(".mp3"))

    def test_the_engine_is_handed_the_voice_and_the_environment(self):
        engine = self._register(StubSpeech())
        self.env["ir.attachment"]._speech_synthesize("hello", voice="alloy")
        text, options = engine.spoken[0]
        self.assertEqual(text, "hello")
        self.assertEqual(options["voice"], "alloy")
        self.assertIsNotNone(options["env"])

    def test_spoken_audio_can_be_filed_against_a_record(self):
        self._register(StubSpeech())
        recording = self._recording()
        attachment = self.env["ir.attachment"]._speech_synthesize(
            "hello",
            res_model=recording._name,
            res_id=recording.id,
        )
        self.assertEqual(attachment.res_model, recording._name)
        self.assertEqual(attachment.res_id, recording.id)

    def test_an_engine_holding_no_credential_does_not_get_the_work(self):
        class Unavailable(StubSpeech):
            name = "unavailable_speech"

            def available(self, env, purpose=None):
                return False

        unusable = Unavailable(b"never-spoken")
        usable = StubSpeech(b"spoken")
        self._only_writers(unusable, usable)
        from odoo.libs.documents import TEXT, get_writers

        self.assertEqual(
            [engine.name for engine in get_writers("audio/mpeg", TEXT)],
            ["unavailable_speech", "stub_speech"],
        )
        attachment = self.env["ir.attachment"]._speech_synthesize("hello")
        self.assertEqual(attachment.raw, b"spoken")
        self.assertEqual(unusable.spoken, [])
        self.assertEqual(len(usable.spoken), 1)

    def test_a_mimetype_no_engine_writes_is_refused(self):
        self._register(StubSpeech())
        with self.assertRaises(UserError):
            self.env["ir.attachment"]._speech_synthesize("hello", mimetype="audio/flac")


@tagged("post_install", "-at_install")
class TestRoundTrip(SpeechCase):
    def test_what_is_spoken_can_be_read_back(self):
        self._register(StubSpeech())
        self._register(StubTranscription(cues=[Cue(0.0, 1.0, "read this aloud", "")]))
        spoken = self.env["ir.attachment"]._speech_synthesize("read this aloud")
        spoken._transcribe()
        self.assertEqual(spoken.transcript_text, "read this aloud")
        self.assertEqual(CUE_FIXTURE[0].text, "the invoice went out")


@tagged("post_install", "-at_install")
class TestOwnerTranscriptionOptions(SpeechCase):
    def test_the_owner_says_how_its_recordings_are_transcribed(self):
        engine = self._register(StubTranscription())
        recording = self._recording()
        attachment = self._audio()
        recording._add_media_segment(attachment, 0, 3000)
        options = {"purpose": "speech.transcription.call", "language": "es"}
        with patch.object(
            type(recording), "_media_transcription_options", return_value=options
        ):
            attachment._transcribe()
        document = engine.calls[-1]
        self.assertEqual(document.options["purpose"], "speech.transcription.call")
        self.assertEqual(document.options["language"], "es")

    def test_a_language_asked_for_wins_over_the_owners(self):
        engine = self._register(StubTranscription())
        recording = self._recording()
        attachment = self._audio()
        recording._add_media_segment(attachment, 0, 3000)
        with patch.object(
            type(recording),
            "_media_transcription_options",
            return_value={"language": "es"},
        ):
            attachment._transcribe(language="en")
        self.assertEqual(engine.calls[-1].options["language"], "en")


@tagged("post_install", "-at_install")
class TestTranscriptionLater(SpeechCase):
    def _job(self, attachment):
        return self.env["ir.job"].search(
            [("identity_key", "=", f"speech.transcribe.{attachment.id}")]
        )

    def test_a_recording_can_wait_and_be_pulled_forward(self):
        self._register(StubTranscription())
        attachment = self._audio()
        later = fields.Datetime.add(fields.Datetime.now(), minutes=40)
        attachment._transcribe_later(eta=later)
        self.assertEqual(self._job(attachment).state, "scheduled")
        attachment._transcribe_later()
        job = self._job(attachment)
        self.assertEqual(len(job), 1)
        self.assertEqual(job.state, "pending")


@tagged("post_install", "-at_install")
class TestAvailabilityFollowsThePurpose(SpeechCase):
    def _owned(self, purpose):
        recording = self._recording()
        attachment = self._audio()
        recording._add_media_segment(attachment, 0, 3000)
        self.patch(
            type(recording),
            "_media_transcription_options",
            lambda self: {"purpose": purpose},
        )
        return recording, attachment

    def test_an_engine_is_asked_for_the_purpose_its_owner_transcribes_under(self):
        engine = self._register(
            PurposeAwareTranscription(serves={"speech.transcription.call"})
        )
        _recording, attachment = self._owned("speech.transcription.call")
        self.assertTrue(attachment.can_transcribe)
        self.assertEqual(engine.asked[-1], "speech.transcription.call")

    def test_an_engine_that_refuses_that_purpose_cannot_transcribe_it(self):
        self._register(PurposeAwareTranscription(serves={"speech.transcription"}))
        _recording, attachment = self._owned("speech.transcription.call")
        self.assertFalse(
            attachment.can_transcribe,
            "the owner's purpose decides, not the generic one",
        )

    def test_an_attachment_no_owner_claims_is_asked_for_no_purpose(self):
        engine = self._register(PurposeAwareTranscription(serves={None}))
        self.assertTrue(self._audio().can_transcribe)
        self.assertIsNone(engine.asked[-1])

    def test_transcribing_refuses_what_the_owners_purpose_may_not_reach(self):
        self._register(PurposeAwareTranscription(serves={"speech.transcription"}))
        _recording, attachment = self._owned("speech.transcription.call")
        with self.assertRaisesRegex(UserError, "No speech engine reads"):
            attachment._transcribe()

    def test_the_timeline_action_asks_for_its_own_purpose(self):
        engine = self._register(PurposeAwareTranscription(serves=set()))
        recording, _attachment = self._owned("speech.transcription.call")
        recording.action_transcribe_media()
        self.assertEqual(engine.asked[-1], "speech.transcription.call")
        self.assertEqual(recording.segment_ids.attachment_id.transcript_state, "none")
