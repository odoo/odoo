# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase


class TestCorsLivechat(HttpCase):
    def test_request_runs_as_the_website_public_user(self):
        public_user = self.env.ref("base.public_user").copy({"login": "website_public_user"})
        self.env.ref("base.default_website").user_id = public_user
        operator = self.env["res.users"].create({"name": "Operator", "login": "operator"})
        self.env["mail.presence"]._update_presence(operator)
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Livechat Channel", "user_ids": [operator.id]},
        )
        self.authenticate("admin", "admin")
        data = self.make_jsonrpc_request(
            "/im_livechat/cors/get_session",
            {
                "channel_id": livechat_channel.id,
                "persisted": True,
            },
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(channel.create_uid, public_user)
