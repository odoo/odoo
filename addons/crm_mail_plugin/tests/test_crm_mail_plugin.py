# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon, mock_auth_method_outlook


class TestCrmMailPlugin(TestMailPluginControllerCommon):
    @mock_auth_method_outlook('employee')
    def test_get_contact_data(self):
        """Check that the leads section is not visible if the user has not access to crm.lead."""
        partner, partner_2 = self.env["res.partner"].create([
            {"name": "Partner 1"},
            {"name": "Partner 2"},
        ])

        data = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"partner_id": partner.id},
        }

        result = self.url_open(
            "/mail_plugin/partner/get",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        ).json()["result"]

        self.assertNotIn("leads", result,
            msg="The user has no access to crm.lead, the leads section should not be visible")

        self.user_test.groups_id |= self.env.ref("sales_team.group_sale_salesman_all_leads")

        lead_1, lead_2 = self.env["crm.lead"].create([
            {"name": "Lead Partner 1", "partner_id": partner.id},
            {"name": "Lead Partner 2", "partner_id": partner_2.id},
        ])

        result = self.url_open(
            "/mail_plugin/partner/get",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        ).json()["result"]

        self.assertIn(
            "leads",
            result,
            msg="The user has access to crm.lead, the leads section should be visible",
        )

        self.assertTrue([lead for lead in result["leads"] if lead["lead_id"] == lead_1.id],
            msg="The first lead belongs to the first partner, it should be returned")
        self.assertFalse([lead for lead in result["leads"] if lead["lead_id"] == lead_2.id],
            msg="The second lead does not belong to the first partner, it should not be returned")
