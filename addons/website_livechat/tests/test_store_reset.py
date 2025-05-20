from odoo.tests import tagged
from odoo.addons.mail.tests.discuss.test_store_reset import TestStoreReset as BaseTestStoreReset
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


@tagged("-at_install", "post_install")
class TestStoreReset(BaseTestStoreReset, TestLivechatCommon):
    def test_store_reset_in_embed_livechat(self):
        self.start_tour(
            "/",
            "website_livechat.store_reset_in_embed_livechat",
        )
