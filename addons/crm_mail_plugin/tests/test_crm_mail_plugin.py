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

        result = self.make_jsonrpc_request("/mail_plugin/partner/get", {"partner_id": partner.id})

        self.assertNotIn("leads", result,
            msg="The user has no access to crm.lead, the leads section should not be visible")

        self.user_test.group_ids |= self.env.ref("sales_team.group_sale_salesman_all_leads")

        lead_1, lead_2 = self.env["crm.lead"].create([
            {"name": "Lead Partner 1", "partner_id": partner.id},
            {"name": "Lead Partner 2", "partner_id": partner_2.id},
        ])

        result = self.make_jsonrpc_request("/mail_plugin/partner/get", {"partner_id": partner.id})

        self.assertIn(
            "leads",
            result,
            msg="The user has access to crm.lead, the leads section should be visible",
        )

        self.assertTrue([lead for lead in result["leads"] if lead["lead_id"] == lead_1.id],
            msg="The first lead belongs to the first partner, it should be returned")
        self.assertFalse([lead for lead in result["leads"] if lead["lead_id"] == lead_2.id],
            msg="The second lead does not belong to the first partner, it should not be returned")

    @mock_auth_method_outlook('employee')
    def test_crm_lead_create_multi_company(self):
        """ Test that creating a record using the mail plugin for a contact belonging to a different company than the
            default company of the user does not result in any issues.
        """
        company_a, company_b = self.env['res.company'].create([
            {'name': 'Company_A'},
            {'name': 'Company_B'},
        ])

        # create contact belonging to Company_B
        contact = self.env['res.partner'].create({
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'company_id': company_b.id,
        })

        # set default company to Company_A
        self.env.user.company_id = company_a.id

        self.user_test.group_ids |= self.env.ref('sales_team.group_sale_salesman_all_leads')

        # Add company_B to user_test to have access to records related to company_B
        self.user_test.write({'company_ids': [(4, company_b.id)]})

        params = {
            'partner_id': contact.id,
            'email_body': 'test body',
            'email_subject': 'test subject',
        }

        result = self.make_jsonrpc_request('/mail_plugin/lead/create', params)

        # Check that the created lead record has the correct company and return the lead_id
        self.assertIn(
            'lead_id',
            result,
            msg='The lead_id should be returned in the response',
        )

        created_lead = self.env['crm.lead'].browse(result['lead_id'])

        self.assertEqual(
            created_lead.company_id,
            company_b,
            msg='The created record should belong to company_B',
        )
