from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.test_res_role import TestResRole
from odoo.tests.common import tagged


@tagged("-at_install", "post_install")
class TestDiscussResRole(TestResRole):
    def test_only_mention_by_role_when_channel_is_accessible(self):
        self.authenticate("admin", "admin")
        role = self.env["res.role"].create({"name": "rd-Discuss"})
        for idx, test_case in enumerate([
            # channel_type, channel_grp, user_grp, is_member, mentionned
            ("channel", None, "base.group_user", False, True),
            ("channel", None, "base.group_user", True, True),
            ("channel", "base.group_system", "base.group_user", False, False),
            ("channel", "base.group_system", "base.group_system", True, True),
            ("group", None, "base.group_user", False, False),
            ("group", None, "base.group_user", True, True),
        ]):
            channel_type, channel_grp, user_grp, is_member, mentionned = test_case
            with self.subTest(
                channel_type=channel_type,
                channel_grp=channel_grp,
                user_grp=user_grp,
                is_member=is_member,
                notified=mentionned,
            ):
                channel = self.env["discuss.channel"].create(
                    {
                        "name": f"channel_{channel_grp}_{user_grp}_{mentionned}",
                        "channel_type": channel_type,
                        "group_public_id": self.env.ref(channel_grp).id if channel_grp else None,
                    }
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
