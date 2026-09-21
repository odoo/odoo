import hashlib
import hmac
import io
import time

from odoo.http import STORED_SESSION_BYTES
from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    RECORDING_MIMETYPES,
    BaseReader,
    Cue,
    register_reader,
    unregister_reader,
)
from odoo.tests import HttpCase, tagged


class StubTranscription(BaseReader):
    name = "stub_upload_transcription"
    mimetypes = RECORDING_MIMETYPES
    yields = (CUES,)
    cost = EXPENSIVE

    def read(self, document):
        return [Cue(0.0, 1.0, "recorded words", "")]


@tagged("post_install", "-at_install")
class TestUploadRoute(HttpCase):
    def setUp(self):
        super().setUp()
        engine = register_reader(StubTranscription())
        self.addCleanup(unregister_reader, engine)
        self.operator = self.env.ref("base.user_admin")
        self.channel = self.env["discuss.channel"]._create_channel(
            name="Recorded", group_id=None
        )
        self.channel.add_members(partner_ids=self.operator.partner_id.ids)

    def _csrf_token(self, session):
        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret")
        max_ts = int(time.time() + 3600)
        msg = f"{session.sid[:STORED_SESSION_BYTES]}{max_ts}".encode()
        return f"{hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()}o{max_ts}"

    def _post(self, mimetype="audio/webm", start=0, end=5000, channel_id=None):
        session = self.authenticate("admin", "admin")
        return self.url_open(
            "/discuss/call/upload_recording",
            data={
                "csrf_token": self._csrf_token(session),
                "channel_id": channel_id or self.channel.id,
                "start_ms": start,
                "end_ms": end,
            },
            files={"ufile": ("chunk.webm", io.BytesIO(b"audio-bytes"), mimetype)},
        )

    def _join(self):
        member = self.channel.with_user(self.operator)._get_or_create_member_for_self()
        member.sudo()._rtc_join_call()
        return member

    def _start(self):
        self.authenticate("admin", "admin")
        return self.call_jsonrpc(
            "/discuss/call/recording/start", {"channel_id": self.channel.id}
        )

    def test_a_member_who_has_not_joined_the_call_is_refused(self):
        response = self._post()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.env["media.segment"].search([]))

    def test_a_chunk_from_a_participant_becomes_a_segment(self):
        self._join()
        self._start()
        response = self._post()
        self.assertEqual(response.status_code, 200)
        segment = self.env["media.segment"].search([], limit=1)
        self.assertTrue(segment)
        self.assertEqual(segment.res_model, "discuss.call.history")
        self.assertEqual(segment.start_ms, 0)
        self.assertEqual(segment.end_ms, 5000)
        self.assertEqual(segment.attachment_id.mimetype, "audio/webm")

    def test_a_recorded_chunk_is_queued_for_transcription(self):
        self._join()
        self._start()
        self._post()
        segment = self.env["media.segment"].search([], limit=1)
        self.assertEqual(segment.attachment_id.speech_state, "queued")

    def test_a_file_that_is_not_a_recording_is_refused(self):
        self._join()
        response = self._post(mimetype="application/pdf")
        self.assertEqual(response.status_code, 415)

    def test_a_span_that_does_not_move_forward_is_refused(self):
        self._join()
        self.assertEqual(self._post(start=5000, end=5000).status_code, 400)
        self.assertEqual(self._post(start=9000, end=1000).status_code, 400)

    def test_an_overlapping_chunk_is_told_the_call_is_already_being_recorded(self):
        self._join()
        self._start()
        self.assertEqual(self._post(start=0, end=5000).status_code, 200)
        self.assertEqual(self._post(start=4000, end=9000).status_code, 409)
        self.assertEqual(len(self.env["media.segment"].search([])), 1)

    def test_a_participant_who_did_not_start_recording_may_not_upload(self):
        self._join()
        response = self._post()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"error": "not_recording"})
        self.assertFalse(self.env["media.segment"].search([]))

    def test_starting_claims_the_call(self):
        self._join()
        self.assertEqual(self._start(), {"recording": True})
        history = self.channel._open_call_history()
        self.assertEqual(
            history.recorder_session_id.channel_member_id.partner_id,
            self.operator.partner_id,
        )

    def test_a_channel_the_caller_does_not_belong_to_is_not_even_named(self):
        other = self.env["discuss.channel"]._create_channel(
            name="Theirs", group_id=None
        )
        self.assertEqual(self._post(channel_id=other.id).status_code, 404)
