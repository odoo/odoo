import json

from odoo.addons.mail_plugin.tests.common import (
    TestMailPluginControllerCommon,
    mock_auth_method_outlook,
)


class TestCrmMailPlugin(TestMailPluginControllerCommon):
    @mock_auth_method_outlook("employee")
    def test_get_contact_data(self):
        partner, partner_2 = self.env["res.partner"].create(
            [
                {"name": "Partner 1"},
                {"name": "Partner 2"},
            ]
        )

        result = self.call_jsonrpc(
            "/mail_plugin/partner/get", {"partner_id": partner.id}
        )

        self.assertNotIn(
            "leads",
            result,
            msg="The user has no access to crm.lead, the leads section should not be visible",
        )

        self.user_test.group_ids |= self.env.ref("sale.group_sale_salesman_all_leads")

        lead_1, lead_2 = self.env["crm.lead"].create(
            [
                {"name": "Lead Partner 1", "partner_id": partner.id},
                {"name": "Lead Partner 2", "partner_id": partner_2.id},
            ]
        )

        result = self.call_jsonrpc(
            "/mail_plugin/partner/get", {"partner_id": partner.id}
        )

        self.assertIn(
            "leads",
            result,
            msg="The user has access to crm.lead, the leads section should be visible",
        )

        self.assertTrue(
            [lead for lead in result["leads"] if lead["lead_id"] == lead_1.id],
            msg="The first lead belongs to the first partner, it should be returned",
        )
        self.assertFalse(
            [lead for lead in result["leads"] if lead["lead_id"] == lead_2.id],
            msg="The second lead does not belong to the first partner, it should not be returned",
        )

    @mock_auth_method_outlook("employee")
    def test_crm_lead_create_multi_company(self):
        company_a, company_b = self.env["res.company"].create(
            [
                {"name": "Company_A"},
                {"name": "Company_B"},
            ]
        )

        contact = self.env["res.partner"].create(
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "company_id": company_b.id,
            }
        )

        self.env.user.company_id = company_a.id

        self.user_test.group_ids |= self.env.ref("sale.group_sale_salesman_all_leads")

        self.user_test.write({"company_ids": [(4, company_b.id)]})

        params = {
            "partner_id": contact.id,
            "email_body": "test body",
            "email_subject": "test subject",
        }

        result = self.call_jsonrpc("/mail_plugin/lead/create", params)

        self.assertIn(
            "lead_id",
            result,
            msg="The lead_id should be returned in the response",
        )

        created_lead = self.env["crm.lead"].browse(result["lead_id"])

        self.assertEqual(
            created_lead.company_id,
            company_b,
            msg="The created record should belong to company_B",
        )
