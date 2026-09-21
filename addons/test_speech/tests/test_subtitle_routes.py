from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestSubtitleRoutes(HttpCase):
    """What a recording says, served to whoever may already hear it.

    `_transcript_vtt` produced valid WebVTT from the day it was written and no route
    served it, so no player could ever show a caption track. These pin the two
    routes that close that, and their access, which is delegated to the same
    resolver `/web/content` uses so a transcript cannot become a way to read a
    recording one cannot fetch.
    """

    def setUp(self):
        super().setUp()
        self.recording = self.env["ir.attachment"].create(
            {"name": "call.mp3", "mimetype": "audio/mpeg", "raw": b"audio"}
        )
        self.recording.sudo().write(
            {
                "transcript_state": "done",
                "transcript_cues": [
                    {
                        "start": 0.0,
                        "end": 1.5,
                        "text": "the invoice went out",
                        "speaker": "",
                    },
                    {"start": 1.5, "end": 3.0, "text": "on Tuesday", "speaker": ""},
                ],
            }
        )
        self.silent = self.env["ir.attachment"].create(
            {"name": "quiet.mp3", "mimetype": "audio/mpeg", "raw": b"audio"}
        )

    def _get(self, attachment, name):
        return self.url_open(f"/speech/attachment/{attachment.id}/{name}")

    def test_a_transcribed_recording_serves_a_caption_track(self):
        self.authenticate("admin", "admin")
        response = self._get(self.recording, "subtitles.vtt")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Type"].startswith("text/vtt"))
        self.assertTrue(response.text.startswith("WEBVTT"))
        self.assertIn("00:00:00.000 --> 00:00:01.500", response.text)
        self.assertIn("the invoice went out", response.text)

    def test_the_same_words_are_served_as_plain_text(self):
        self.authenticate("admin", "admin")
        response = self._get(self.recording, "transcript.txt")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Type"].startswith("text/plain"))
        self.assertEqual(response.text, "the invoice went out\non Tuesday")

    def test_an_untranscribed_recording_is_not_found_rather_than_empty(self):
        self.authenticate("admin", "admin")
        self.assertEqual(self._get(self.silent, "subtitles.vtt").status_code, 404)

    def test_a_recording_that_does_not_exist_is_not_found(self):
        self.authenticate("admin", "admin")
        response = self.url_open("/speech/attachment/999999999/subtitles.vtt")
        self.assertEqual(response.status_code, 404)

    def test_someone_who_may_not_read_the_recording_may_not_read_its_words(self):
        self.assertEqual(self._get(self.recording, "subtitles.vtt").status_code, 404)
        self.assertEqual(self._get(self.recording, "transcript.txt").status_code, 404)
