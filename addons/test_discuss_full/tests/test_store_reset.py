from odoo.tests import tagged
from odoo.addons.mail.tests.discuss.test_store_reset import TestStoreReset as BaseTestStoreReset
from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon


@tagged("-at_install", "post_install")
class TestStoreReset(BaseTestStoreReset, TestGetOperatorCommon):
    def test_store_reset_in_embed_livechat(self):
        operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Support Channel", "user_ids": [operator.id]}
        )
        self.start_tour(
            f"/odoo/im_livechat/channel/{livechat_channel.id}",
            "test_discuss_full.store_reset_in_embed_livechat",
        )
