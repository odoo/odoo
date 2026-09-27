# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC

from odoo import fields
from odoo.tests.common import HttpCase

from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools import discuss, jwt


class TestCloudStorageRtc(MailCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create(
            {
                "name": "Recorded Call",
                "channel_type": "group",
            },
        )
        call_start = fields.Datetime.now()
        cls.call_history = cls.env["discuss.call.history"].create(
            {
                "channel_id": cls.channel.id,
                "start_dt": call_start,
            },
        )
        cls.call_start_ms = int(call_start.replace(tzinfo=UTC).timestamp() * 1000)
        cls.env["ir.config_parameter"].set_str(
            "mail.sfu_server_key",
            "u6bsUQEWrHdKIuYplirRnbBmLbrKV5PxKG7DtA71mng=",
        )
        cls.env["ir.config_parameter"].set_str("cloud_storage_provider", "dummy")

    def setUp(self):
        super().setUp()
        self.patch(
            self.env.registry["ir.attachment"],
            "_generate_cloud_storage_url",
            lambda attachment: f"https://storage.example.com/{attachment.id}",
        )
        self.patch(
            self.env.registry["ir.attachment"],
            "_generate_cloud_storage_upload_info",
            lambda attachment: {
                "url": attachment.url,
                "method": "PUT",
                "headers": {"Content-Type": attachment.mimetype},
                "response_status": 201,
            },
        )

    def _recording_request(
        self,
        endpoint="routing",
        *,
        method="POST",
        token=None,
        **params,
    ):
        if token is None:
            token = jwt.sign(
                {
                    "iat": self.call_start_ms // 1000,
                    "user_id": self.user_employee.id,
                },
                discuss.get_derived_sfu_key(self.env, self.channel.id),
                ttl=60,
                algorithm=jwt.Algorithm.HS256,
            )
        return self.url_open(
            f"/mail/rtc/recording/{self.call_history.id}/{endpoint}",
            method=method,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "start_ms": self.call_start_ms + 1_000,
                "end_ms": self.call_start_ms + 3_000,
                **params,
            },
        )

    def test_recording_is_published_after_upload(self):
        with self.mock_mail_gateway():
            with self.assertBus([]):
                response = self._recording_request(mimetype="audio/ogg")
            self.assertEqual(response.status_code, 200)
            self.call_history.invalidate_recordset(["artifact_ids"])
            artifact = self.call_history.artifact_ids
            self.assertEqual(len(artifact), 1)
            self.assertEqual(artifact.recording_started_by_id, self.user_employee)
            self.assertEqual((artifact.start_ms, artifact.end_ms), (1_000, 3_000))
            self.assertTrue(artifact.recording_upload_pending)
            self.assertEqual(artifact.media_id.mimetype, "audio/ogg")
            self.assertEqual(artifact.media_id.type, "cloud_storage")
            self.assertEqual(
                artifact.media_id.name,
                f"call_history_{self.call_history.id}_recording_{artifact.id}",
            )
            self.assertFalse(self.call_history.has_recording)
            self.assertFalse(self.call_history.has_audio)
            self.assertFalse(self._new_mails)
            upload_info = {
                "destination": artifact.media_id.url,
                "method": "PUT",
                "headers": {"Content-Type": "audio/ogg"},
                "response_status": 201,
                "requires_completion": True,
            }
            self.assertEqual(response.json(), upload_info)
            with self.assertBus(
                BusResult(
                    self.channel,
                    "mail.record/insert",
                    {
                        "discuss.call.history": [
                            {
                                "id": self.call_history.id,
                                "channel_id": self.channel.id,
                                "has_audio": True,
                                "has_recording": True,
                                "has_video": False,
                            },
                        ],
                    },
                ),
            ):
                completed = self._recording_request("complete")
            self.assertEqual(completed.status_code, 204)
            artifact.invalidate_recordset(["recording_upload_pending"])
            self.assertFalse(artifact.recording_upload_pending)
            mail = self.assertMailMailWRecord(
                artifact,
                self.partner_employee,
                "outgoing",
                content="Your meeting recording is available in Odoo.",
            )
            self.assertIn(
                f"/odoo/discuss.call.history/{self.call_history.id}",
                mail.body_html,
            )
            self.assertEqual(self._new_mails, mail)

    def test_recording_routing_rejects_non_media(self):
        with self.mock_mail_gateway(), self.assertBus([]):
            response = self._recording_request(mimetype="text/plain")
            self.assertEqual(response.status_code, 400)
            self.call_history.invalidate_recordset(["artifact_ids"])
            self.assertFalse(self.call_history.artifact_ids)
            self.assertFalse(self._new_mails)

    def test_recording_routing_requires_post(self):
        with self.mock_mail_gateway(), self.assertBus([]):
            response = self._recording_request(method="GET", mimetype="audio/ogg")
            self.assertEqual(response.status_code, 405)
            self.call_history.invalidate_recordset(["artifact_ids"])
            self.assertFalse(self.call_history.artifact_ids)
            self.assertFalse(self._new_mails)

    def test_recording_completion_rejects_unknown_destination(self):
        with self.mock_mail_gateway(), self.assertBus([]):
            response = self._recording_request("complete")
            self.assertEqual(response.status_code, 404)
            self.call_history.invalidate_recordset(["artifact_ids"])
            self.assertFalse(self.call_history.artifact_ids)
            self.assertFalse(self._new_mails)

    def test_recording_routes_reject_invalid_tokens(self):
        missing_expiration = jwt._generate_jwt(
            {"iat": self.call_start_ms // 1000},
            discuss.get_derived_sfu_key(self.env, self.channel.id),
            algorithm=jwt.Algorithm.HS256,
        )
        with self.mock_mail_gateway(), self.assertBus([]):
            for endpoint in ("routing", "complete"):
                for token in ("", "NQ.e30.AAAA", missing_expiration):
                    with self.subTest(endpoint=endpoint, token=token):
                        response = self._recording_request(endpoint, token=token)
                        self.assertEqual(response.status_code, 404)
            self.call_history.invalidate_recordset(["artifact_ids"])
            self.assertFalse(self.call_history.artifact_ids)
            self.assertFalse(self._new_mails)
