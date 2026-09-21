from datetime import timedelta

from odoo import fields
from odoo.libs.documents import Cue
from odoo.tests import tagged

from .common import SpeechCase, StubTranscription


@tagged("post_install", "-at_install")
class TestRetention(SpeechCase):
    def test_a_timeline_that_keeps_everything_sets_no_expiry(self):
        segment = self._recording()._add_media_segment(self._audio(), 0, 1000)
        self.assertFalse(segment.attachment_id.content_expires_at)

    def test_filing_a_segment_stamps_the_owners_retention_from_arrival(self):
        recording = self._recording()
        recording.retention_days = 30
        attachment = self._audio()
        segment = recording._add_media_segment(attachment, 0, 1000)
        self.assertEqual(
            segment.attachment_id.content_expires_at,
            attachment.create_date + timedelta(days=30),
        )

    def test_a_changed_policy_restamps_what_is_not_released_yet(self):
        recording = self._recording()
        recording.retention_days = 30
        kept = recording._add_media_segment(self._audio(name="a.mp3"), 0, 1000)
        recording.retention_days = 0
        recording._restamp_media_expiry()
        self.assertFalse(kept.attachment_id.content_expires_at)

    def test_expired_audio_goes_and_what_was_said_stays(self):
        self._register(
            StubTranscription(cues=[Cue(0.0, 2.0, "guardamos esto", "SPEAKER_0")])
        )
        recording = self._recording()
        recording.retention_days = 30
        attachment = self._audio()
        segment = recording._add_media_segment(attachment, 0, 2000)
        attachment._transcribe()
        attachment.content_expires_at = fields.Datetime.now() - timedelta(days=1)
        self.env["ir.attachment"]._gc_expired_content()
        self.assertTrue(segment.content_released_at)
        self.assertFalse(attachment.raw)
        self.assertEqual(attachment.transcript_cues[0]["text"], "guardamos esto")
        self.assertIn("guardamos esto", attachment.sudo().index_content)
        self.assertEqual(recording.timeline_transcript, "guardamos esto")
        self.assertEqual(len(attachment.speaker_ids), 1)
