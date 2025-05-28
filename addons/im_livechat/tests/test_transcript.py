from odoo.tests.common import tagged
from odoo.tools import mute_logger
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("-at_install", "post_install")
class TestImLivechatTranscript(TestImLivechatCommon, HttpCaseWithUserDemo):
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
