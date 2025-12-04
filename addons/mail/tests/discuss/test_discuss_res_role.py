# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.test_res_role import TestResRole


class TestDiscussResRole(TestResRole):
    def test_only_mention_by_role_when_channel_is_accessible(self):
        self.authenticate("admin", "admin")
        role = self.env["res.role"].create({"name": "rd-Discuss"})
        for idx, test_case in enumerate([
            # channel_type, access_type, user_grp, is_member, mentionned
            ("channel", "public", "base.group_user", False, True),
            ("channel", "public", "base.group_user", True, True),
            ("channel", "internal", "base.group_user", False, True),
            ("channel", "internal", "base.group_user", True, True),
            ("channel", "invite_only", "base.group_user", False, False),
            ("channel", "invite_only", "base.group_user", True, True),
            ("group", None, "base.group_user", False, False),
            ("group", None, "base.group_user", True, True),
        ]):
            channel_type, access_type, user_grp, is_member, mentionned = test_case
            with self.subTest(
                channel_type=channel_type,
                access_type=access_type,
                user_grp=user_grp,
                is_member=is_member,
                notified=mentionned,
            ):
                channel = self.env["discuss.channel"].create(
                    {
                        "access_type": access_type,
                        "channel_type": channel_type,
                        "name": f"channel_{access_type}_{user_grp}_{mentionned}",
                    },
                )
                user = mail_new_test_user(
                    self.env, login=f"user_{user_grp}_{idx}", role_ids=role.ids, groups=user_grp
                )
                if is_member:
                    channel.add_members(partner_ids=user.partner_id.ids)
                data = self.make_jsonrpc_request(
                    "/mail/message/post",
                    {
                        "thread_model": "discuss.channel",
                        "thread_id": channel.id,
                        "post_data": {
                            "body": "irrelevant",
                            "message_type": "comment",
                            "role_ids": role.ids,
                            "subtype_xmlid": "mail.mt_note",
                        },
                    },
                )
                formatted_partner = user.partner_id.id
                message = next(filter(lambda m: m["id"] == data["message_id"], data["store_data"]["mail.message"]))
                if mentionned:
                    self.assertIn(formatted_partner, message["partner_ids"])
                else:
                    self.assertNotIn(formatted_partner, message["partner_ids"])
