from odoo.tests.common import JsonRpcException, tagged
from odoo.tools import mute_logger
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("-at_install", "post_install")
class TestImLivechatTranscript(TestImLivechatCommon, HttpCaseWithUserDemo, HttpCaseWithUserPortal):
    def test_download_transcript(self):
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
        )
        res = self.url_open(f"/im_livechat/download_transcript/{data['channel_id']}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "application/pdf")

    def test_download_transcript_non_member(self):
        self.authenticate("demo", "demo")
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.authenticate(None, None)
        self.assertFalse(chat.is_member)
        with mute_logger("odoo.http"):
            res = self.url_open(f"/im_livechat/download_transcript/{data['channel_id']}")
        self.assertEqual(res.status_code, 404)

    def test_email_transcript_portal_user(self):
        self.authenticate(self.user_portal.login, self.user_portal.login)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
        )
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.make_jsonrpc_request(
                "/im_livechat/email_livechat_transcript",
                {"channel_id": data["channel_id"], "email": self.partner_portal.email},
            )
