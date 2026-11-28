# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestDiscussChannel(TransactionCase):
    def test_access_channel_from_lead(self):
        test_cases = [
            # user_grp - has_lead - expected_result
            ("base.group_public", False, False),
            ("base.group_public", True, False),
            ("base.group_portal", False, False),
            ("base.group_portal", True, False),
            ("base.group_user", False, False),
            ("base.group_user", True, False),
            ("sales_team.group_sale_salesman", False, False),
            ("sales_team.group_sale_salesman", True, True),
        ]
        for idx, case in enumerate(test_cases):
            user_grp, has_lead, expected_result = case
            crm_lead = self.env["crm.lead"]
            if has_lead:
                crm_lead = self.env["crm.lead"].create({"name": f"ticket_{idx}"})
            channel = self.env["discuss.channel"].create(
                {
                    "name": f"channel_{idx}",
                    "channel_type": "group",
                    "lead_ids": crm_lead.ids,
                }
            )
            user = new_test_user(self.env, login=f"user_{idx}_{user_grp}", groups=user_grp)
            self.assertEqual(
                channel.with_user(user).has_access("read"),
                expected_result,
                f"user_grp={user_grp}, has_lead={has_lead}, expected_result={expected_result}",
            )

    def test_cannot_link_lead_to_restricted_channel(self):
        user = new_test_user(self.env, login="bob_user", groups="sales_team.group_sale_salesman")
        channel = (
            self.env["discuss.channel"]
            .create(
                {
                    "name": "Private conversation",
                    "channel_type": "group",
                }
            )
            .with_user(user)
        )
        self.assertFalse(channel.has_access("read"))
        with self.assertRaises(
            AccessError,
            msg="You cannot create a lead linked to a channel you don't have access to.",
        ):
            self.env["crm.lead"].with_user(user).create(
                {"name": "lead", "origin_channel_id": channel.id}
            )

        with self.assertRaises(
            AccessError,
            msg="You cannot create a lead linked to a restricted channel through context defaults.",
        ):
            self.env["crm.lead"].with_user(user).with_context(
                default_origin_channel_id=channel.id,
            ).create({"name": "lead"})

        lead = self.env["crm.lead"].with_user(user).create({"name": "lead"})
        with self.assertRaises(
            AccessError,
            msg="You cannot update a lead and link it to a channel you don't have access to.",
        ):
            lead.write({"origin_channel_id": channel.id})

    def test_create_lead_when_channel_has_deleted_message(self):
        user = new_test_user(self.env, login="bob_user", groups="sales_team.group_sale_salesman")
        channel = self.env["discuss.channel"].create({
            "name": "Customer conversation",
            "channel_type": "group",
            "channel_partner_ids": [Command.link(user.partner_id.id)],
        })
        message = channel.message_post(
            author_id=user.partner_id.id, body="Hello, how can I help you?", message_type="comment",
        )
        channel._message_update_content(message, body="")
        self.env.invalidate_all()
        self.assertFalse(channel.lead_ids)
        channel.with_user(user).execute_command_lead(body="/lead BobLead")
        self.assertEqual(channel.lead_ids.name, "BobLead")
        self.assertFalse(channel.lead_ids.description)
