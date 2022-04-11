# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('mail_thread', 'mail_gateway')
class NewLeadNotification(TestCrmCommon):

    @users('user_sales_manager')
    def test_lead_message_get_suggested_recipient(self):
        """ Test '_message_get_suggested_recipients' and its override in lead. """
        lead_format, lead_multi, lead_from, lead_partner = self.env['crm.lead'].create([
            {
                'email_from': '"New Customer" <new.customer.format@test.example.com>',
                'name': 'Test Suggestion (email_from with format)',
                'partner_name': 'Format Name',
                'user_id': self.user_sales_leads.id,
            }, {
                'email_from': 'new.customer.multi.1@test.example.com, new.customer.2@test.example.com',
                'name': 'Test Suggestion (email_from multi)',
                'partner_name': 'Multi Name',
                'user_id': self.user_sales_leads.id,
            }, {
                'email_from': 'new.customer.simple@test.example.com',
                'name': 'Test Suggestion (email_from)',
                'partner_name': 'Std Name',
                'user_id': self.user_sales_leads.id,
            }, {
                'name': 'Test Suggestion (partner_id)',
                'partner_id': self.contact_1.id,
                'user_id': self.user_sales_leads.id,
            }
        ])
        for lead, expected_suggested in zip(
            lead_format + lead_multi + lead_from + lead_partner,
            [(False, '"New Customer" <new.customer.format@test.example.com>', None, 'Customer Email'),
             (False, '"Multi Name" <new.customer.multi.1@test.example.com,new.customer.2@test.example.com>', None, 'Customer Email'),
             (False, '"Std Name" <new.customer.simple@test.example.com>', None, 'Customer Email'),
             (self.contact_1.id, '"Philip J Fry" <philip.j.fry@test.example.com>', self.contact_1.lang, 'Customer'),
            ]
        ):
            with self.subTest(lead=lead, email_from=lead.email_from):
                res = lead._message_get_suggested_recipients()[lead.id]
                self.assertEqual(len(res), 1)
                self.assertEqual(res[0], expected_suggested)

    def test_new_lead_notification(self):
        """ Test newly create leads like from the website. People and channels
        subscribed to the Sales Team shoud be notified. """
        # subscribe a partner and a channel to the Sales Team with new lead subtype
        sales_team_1 = self.env['crm.team'].create({
            'name': 'Test Sales Team',
            'alias_name': 'test_sales_team',
        })

        subtype = self.env.ref("crm.mt_salesteam_lead")
        sales_team_1.message_subscribe(partner_ids=[self.user_sales_manager.partner_id.id], subtype_ids=[subtype.id])

        # Imitate what happens in the controller when somebody creates a new
        # lead from the website form
        lead = self.env["crm.lead"].with_context(mail_create_nosubscribe=True).sudo().create({
            "contact_name": "Somebody",
            "description": "Some question",
            "email_from": "somemail@example.com",
            "name": "Some subject",
            "partner_name": "Some company",
            "team_id": sales_team_1.id,
            "phone": "+0000000000"
        })
        # partner and channel should be auto subscribed
        self.assertIn(self.user_sales_manager.partner_id, lead.message_partner_ids)

        msg = lead.message_ids[0]
        self.assertIn(self.user_sales_manager.partner_id, msg.notified_partner_ids)

        # The user should have a new unread message
        lead_user = lead.with_user(self.user_sales_manager)
        self.assertTrue(lead_user.message_needaction)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_new_lead_from_email_multicompany(self):
        company0 = self.env.company
        company1 = self.env['res.company'].create({'name': 'new_company'})

        self.env.user.write({
            'company_ids': [(4, company0.id, False), (4, company1.id, False)],
        })

        crm_team_model = self.env['ir.model'].search([('model', '=', 'crm.team')])
        crm_lead_model = self.env['ir.model'].search([('model', '=', 'crm.lead')])
        self.env["ir.config_parameter"].sudo().set_param("mail.catchall.domain", 'aqualung.com')

        crm_team0 = self.env['crm.team'].create({
            'name': 'crm team 0',
            'company_id': company0.id,
        })
        crm_team1 = self.env['crm.team'].create({
            'name': 'crm team 1',
            'company_id': company1.id,
        })

        mail_alias0 = self.env['mail.alias'].create({
            'alias_name': 'sale_team_0',
            'alias_model_id': crm_lead_model.id,
            'alias_parent_model_id': crm_team_model.id,
            'alias_parent_thread_id': crm_team0.id,
            'alias_defaults': "{'type': 'opportunity', 'team_id': %s}" % crm_team0.id,
        })
        mail_alias1 = self.env['mail.alias'].create({
            'alias_name': 'sale_team_1',
            'alias_model_id': crm_lead_model.id,
            'alias_parent_model_id': crm_team_model.id,
            'alias_parent_thread_id': crm_team1.id,
            'alias_defaults': "{'type': 'opportunity', 'team_id': %s}" % crm_team1.id,
        })

        crm_team0.write({'alias_id': mail_alias0.id})
        crm_team1.write({'alias_id': mail_alias1.id})

        new_message0 = """MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: <blablabla0>
Subject: sale team 0 in company 0
From:  A client <client_a@someprovider.com>
To: sale_team_0@aqualung.com
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message</div>

--000000000000a47519057e029630--
"""

        new_message1 = """MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: <blablabla1>
Subject: sale team 1 in company 1
From:  B client <client_b@someprovider.com>
To: sale_team_1@aqualung.com
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message bis</div>

--000000000000a47519057e029630--
"""
        crm_lead0_id = self.env['mail.thread'].message_process('crm.lead', new_message0)
        crm_lead1_id = self.env['mail.thread'].message_process('crm.lead', new_message1)

        crm_lead0 = self.env['crm.lead'].browse(crm_lead0_id)
        crm_lead1 = self.env['crm.lead'].browse(crm_lead1_id)

        self.assertEqual(crm_lead0.team_id, crm_team0)
        self.assertEqual(crm_lead1.team_id, crm_team1)

        self.assertEqual(crm_lead0.company_id, company0)
        self.assertEqual(crm_lead1.company_id, company1)
