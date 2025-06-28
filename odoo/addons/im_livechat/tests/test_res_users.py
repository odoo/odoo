from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLiveChatResUsers(TransactionCase):

    def test_livechat_create_res_users(self):
        access_user = new_test_user(
            self.env,
            login="admin_access",
            name="admin_access",
            groups="base.group_erp_manager,base.group_partner_manager",
        )
        access_user.with_user(access_user.id).create({
            "login": "test_can_be_created",
            "name": "test_can_be_created",
            "livechat_username": False,
            "livechat_lang_ids": [],
        })
