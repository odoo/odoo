# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDiscussChannelAccess(HttpCase):
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
                    "livechat_operator_id": self.env.user.partner_id.id,
                    "channel_type": "livechat",
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
                    "name": f"Visitor #11",
                    "livechat_operator_id": self.env.user.partner_id.id,
                    "channel_type": "livechat",
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

        lead = self.env["crm.lead"].with_user(user).create({"name": "lead"})
        with self.assertRaises(
            AccessError,
            msg="You cannot update a lead and link it to a channel you don't have access to.",
        ):
            lead.write({"origin_channel_id": channel.id})
