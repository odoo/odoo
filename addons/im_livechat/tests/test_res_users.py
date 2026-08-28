# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase


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

    def test_livechat_expertise_ids_write_keeps_previous_tags(self):
        user = new_test_user(self.env, login="livechat_operator")
        expertise_1, expertise_2 = self.env["im_livechat.expertise"].create([
            {"name": "Expertise 1"},
            {"name": "Expertise 2"},
        ])

        user.with_user(user).write({"livechat_expertise_ids": [Command.link(expertise_1.id)]})
        self.env.invalidate_all()
        self.assertEqual(user.livechat_expertise_ids, expertise_1)

        user.with_user(user).write({"livechat_expertise_ids": [Command.link(expertise_2.id)]})
        self.env.invalidate_all()
        self.assertEqual(user.livechat_expertise_ids, expertise_1 + expertise_2)
