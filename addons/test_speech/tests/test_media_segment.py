from psycopg.errors import CheckViolation, UniqueViolation

from odoo.exceptions import AccessError, ValidationError
from odoo.libs.documents import Cue
from odoo.tests import tagged

from .common import SpeechCase, StubTranscription


@tagged("post_install", "-at_install")
class TestMediaSegment(SpeechCase):
    def test_two_segments_may_not_cover_the_same_moment(self):
        recording = self._recording()
        recording._add_media_segment(self._audio("a.mp3"), 0, 2000)
        with self.assertRaises(ValidationError):
            recording._add_media_segment(self._audio("b.mp3"), 1500, 3000)

    def test_segments_that_touch_do_not_overlap(self):
        recording = self._recording()
        recording._add_media_segment(self._audio("a.mp3"), 0, 2000)
        recording._add_media_segment(self._audio("b.mp3"), 2000, 4000)
        self.assertEqual(len(recording.segment_ids), 2)

    def test_two_owners_may_hold_the_same_moment(self):
        first = self._recording("first")
        second = self._recording("second")
        first._add_media_segment(self._audio("a.mp3"), 0, 2000)
        second._add_media_segment(self._audio("b.mp3"), 0, 2000)
        self.assertEqual(len(first.segment_ids), 1)
        self.assertEqual(len(second.segment_ids), 1)

    def test_a_segment_must_end_after_it_starts(self):
        recording = self._recording()
        with self.assertRaises(CheckViolation):
            recording._add_media_segment(self._audio(), 2000, 2000)

    def test_deleting_a_segment_deletes_its_media(self):
        recording = self._recording()
        attachment = self._audio()
        segment = recording._add_media_segment(attachment, 0, 1000)
        segment.unlink()
        self.assertFalse(attachment.exists())

    def test_deleting_the_owner_deletes_its_segments(self):
        recording = self._recording()
        recording._add_media_segment(self._audio(), 0, 1000)
        segments = self.env["media.segment"]._of(recording)
        recording.unlink()
        self.assertFalse(segments.exists())

    def test_one_media_file_belongs_to_one_segment(self):
        first = self._recording("first")
        second = self._recording("second")
        attachment = self._audio()
        first._add_media_segment(attachment, 0, 1000)
        with self.assertRaises(UniqueViolation):
            second._add_media_segment(attachment, 0, 1000)

    def test_a_segment_knows_its_owner(self):
        recording = self._recording()
        segment = recording._add_media_segment(self._audio(), 0, 1000)
        self.assertEqual(segment._owner(), recording)

    def test_duration_is_the_span_it_covers(self):
        recording = self._recording()
        segment = recording._add_media_segment(self._audio(), 500, 2000)
        self.assertEqual(segment.duration_ms, 1500)


class TestSegmentOwnership(SpeechCase):
    def setUp(self):
        super().setUp()
        self.stranger = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "stranger",
                    "login": "speech_stranger",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )

    def _as_stranger(self):
        return self.env(user=self.stranger, su=False)

    def _portal_user(self):
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "portal",
                    "login": "speech_portal",
                    "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
                }
            )
        )

    def test_a_stranger_may_not_file_media_against_a_record_they_cannot_write(self):
        recording = self._recording()
        attachment = self._audio()
        with self.assertRaises(AccessError):
            self._as_stranger()["media.segment"].create(
                {
                    "res_model": recording._name,
                    "res_id": recording.id,
                    "attachment_id": attachment.id,
                    "start_ms": 0,
                    "end_ms": 1000,
                }
            )

    def test_the_recorder_files_media_under_sudo_and_is_not_refused(self):
        recording = self._recording()
        segment = recording._add_media_segment(self._audio(), 0, 1000)
        self.assertTrue(segment.id)
        self.assertEqual(segment._owner(), recording)

    def test_a_reader_of_the_owner_reads_its_segments(self):
        recording = self._recording()
        segment = recording._add_media_segment(self._audio(), 0, 1000)
        as_stranger = segment.with_env(self._as_stranger())
        self.assertEqual(as_stranger.start_ms, 0)
        self.assertEqual(
            self._as_stranger()["media.segment"].search([("id", "=", segment.id)]),
            as_stranger,
        )

    def test_someone_who_cannot_read_the_owner_cannot_read_its_transcript(self):
        recording = self._recording()
        segment = recording._add_media_segment(self._audio(), 0, 1000)
        segment.attachment_id.sudo().transcript_cues = [
            {"start": 0.0, "end": 1.0, "text": "secret", "speaker": ""}
        ]
        portal_env = self.env(user=self._portal_user(), su=False)
        with self.assertRaises(AccessError):
            segment.with_env(portal_env).read(["transcript_cues"])
        self.assertFalse(
            portal_env["media.segment"].search([("id", "=", segment.id)]),
            "a segment whose owner is unreadable is not even found",
        )


class TestTheMixinDoesNotSquatAConsumersFieldNames(SpeechCase):
    """`mixin.media.timeline` is applied to models it does not own.

    A generic mixin that claims a generic field name takes over whatever the
    consumer already declared under it, and the merge is order-independent: once
    `compute` is in the merged attrs nothing removes it, and `store` then
    defaults to False. The consumer's column survives, orphaned, while every
    write to it is silently discarded.
    """

    def _owner_with_its_own_transcript(self):
        return self.env["speech.test.call.with.own.transcript"].create({})

    def test_an_owners_own_transcript_field_is_still_stored_after_the_mixin(self):
        field = self.env["speech.test.call.with.own.transcript"]._fields["transcript"]
        self.assertTrue(field.store)
        self.assertFalse(field.compute)
        self.assertFalse(field.readonly)

    def test_an_owners_own_transcript_still_survives_a_write_and_a_reread(self):
        owner = self._owner_with_its_own_transcript()
        owner.transcript = "what the vendor was paid to produce"
        owner.flush_recordset()
        owner.invalidate_recordset()
        self.assertEqual(owner.transcript, "what the vendor was paid to produce")

    def test_the_mixin_offers_its_own_roll_up_under_a_namespaced_name(self):
        owner = self._owner_with_its_own_transcript()
        attachment = self._audio()
        self._register(StubTranscription(cues=[Cue(0.0, 1.0, "from the segments", "")]))
        owner._add_media_segment(attachment, 0, 1000)
        attachment._transcribe()
        self.assertEqual(owner.timeline_transcript, "from the segments")
        self.assertFalse(owner.transcript)

    def test_no_mixin_field_takes_a_bare_name_a_consumer_would_plausibly_own(self):
        declared = set(self.env["mixin.media.timeline"]._fields) - set(
            self.env["base"]._fields
        )
        squatters = {
            "transcript",
            "transcript_text",
            "transcript_state",
            "duration",
            "state",
            "name",
            "summary",
            "status",
        }
        self.assertEqual(declared & squatters, set())
