# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests import tagged, users
from odoo.tools import formataddr, mute_logger


@tagged('mail_thread', 'mail_gateway')
class NewLeadNotification(TestCrmCommon):
    """ Test mail features support on lead + specific overrides and support """

    @classmethod
    def setUpClass(cls):
        """ Activate some langs to test lang propagation in various mail flows """
        super(NewLeadNotification, cls).setUpClass()
        cls.test_email = '"Test Email" <test.email@example.com>'
        model_lang = cls.env['res.lang'].sudo().with_context(active_test=False)

        # Create a lead with an inactive language -> should ignore the preset language
        cls.lang_fr = model_lang.search([('code', '=', 'fr_FR')])
        if not cls.lang_fr:
            cls.lang_fr = model_lang._create_lang('fr_FR')
        # set French language as inactive then try to call "_message_get_suggested_recipients"
        # -> lang code should be ignored
        cls.lang_fr.active = False
        # Create a lead with an active language -> should keep the preset language for recipients
        cls.lang_en = model_lang.search([('code', '=', 'en_US')])
        if not cls.lang_en:
            cls.lang_en = model_lang._create_lang('en_US')
        # set American English language as active then try to call "_message_get_suggested_recipients"
        # -> lang code should be kept
        cls.lang_en.active = True

    @users('user_sales_manager')
    def test_lead_message_get_suggested_recipients_email(self):
        """ Test '_message_get_suggested_recipients' and its override in lead
        when dealing with various emails. """
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
        for lead, expected in zip(
            lead_format + lead_multi + lead_from + lead_partner,
            [(False, '"New Customer" <new.customer.format@test.example.com>', None, 'Customer Email',
              {'company_name': 'Format Name', 'email': 'new.customer.format@test.example.com',
               'name': 'Format Name', 'user_id': self.user_sales_leads.id,
               'team_id': self.sales_team_1.id,
              }),
             (False, '"Multi Name" <new.customer.multi.1@test.example.com,new.customer.2@test.example.com>', None, 'Customer Email',
              {'company_name': 'Multi Name', 'email': 'new.customer.multi.1@test.example.com',
                'name': 'Multi Name', 'user_id': self.user_sales_leads.id,
                'team_id': self.sales_team_1.id,
              }),
             (False, '"Std Name" <new.customer.simple@test.example.com>', None, 'Customer Email',
              {'company_name': 'Std Name', 'email': 'new.customer.simple@test.example.com',
               'name': 'Std Name', 'user_id': self.user_sales_leads.id,
               'team_id': self.sales_team_1.id,
              }),
             (self.contact_1.id, '"Philip J Fry" <philip.j.fry@test.example.com>', self.contact_1.lang, 'Customer',
              {}),  # creation values only if not partner
            ]
        ):
            with self.subTest(lead=lead, lead_name=lead.name, email_from=lead.email_from):
                res = lead._message_get_suggested_recipients()[lead.id]
                self.assertEqual(len(res), 1)
                self.assertEqual(res[0][:4], expected[:4])
                customer_data = expected[4]
                if not customer_data:
                    self.assertFalse(res[0][4])
                else:
                    for partner_fname in customer_data:
                        found, expected = res[0][4][partner_fname], customer_data[partner_fname]
                        self.assertEqual(
                            found, expected,
                            f'Lead suggested customer: wrong value for {partner_fname} got {found} instead of {expected}')

    @users('user_sales_manager')
    def test_lead_message_get_suggested_recipients_langs(self):
        """This test checks that creating a contact from a lead with an inactive
        language will ignore the language while creating a contact from a lead
        with an active language will take it into account """
        leads = self.env['crm.lead'].create([
            {
                'email_from': self.test_email,
                'lang_id': self.lang_fr.id,
                'name': 'TestLead',
            }, {
                'email_from': self.test_email,
                'lang_id': self.lang_en.id,
                'name': 'TestLead',
            }
        ])
        expected_list = [
            (False, self.test_email, None, 'Customer Email', {'lang': 'fr_FR'}),
            (False, self.test_email, 'en_US', 'Customer Email', {'lang': 'en_US'}),
        ]
        for lead, expected in zip(leads, expected_list):
            with self.subTest(lead=lead):
                res = lead._message_get_suggested_recipients()[lead.id]
                self.assertEqual(len(res), 1)
                self.assertEqual(res[0][:4], expected[:4])
                for partner_fname in expected[4]:
                    found = res[0][4][partner_fname]
                    expected = expected[4][partner_fname]
                    self.assertEqual(
                        found, expected,
                        f'Lead suggested customer: wrong value for {partner_fname} got {found} instead of {expected}')

    @users('user_sales_manager')
    def test_lead_message_get_suggested_recipients_values_for_create(self):
        """Check default creates value used when creating client from suggested
        recipients (customer)."""
        lead_details_for_contact = {
            'title': self.env.ref('base.res_partner_title_mister').id,
            'street': '3rd Floor, Room 3-C',
            'street2': '123 Arlington Avenue',
            'zip': '13202',
            'city': 'New York',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
            'website': 'https://www.arlington123.com/3f3c',
            'phone': '678-728-0949',
            'mobile': '661-606-0781',
            'function': 'Delivery Boy',
            'team_id': self.sales_team_1.id,
            'user_id': self.user_sales_manager.id,
        }

        for partner_name, name, email in [
            (False, 'Test', 'test_default_create@example.com'),
            ('Delivery Boy company', 'Test With Company', 'default_create_with_partner@example.com'),
            ('Delivery Boy company', '', 'default_create_with_partner_no_name@example.com'),
        ]:
            formatted_email = formataddr((name, email)) if name else formataddr((partner_name, email))
            with self.subTest(partner_name=partner_name):
                lang = self.env['res.lang'].sudo().search([], limit=1)[0]
                description = '<p>Top</p>'
                lead1 = self.env['crm.lead'].create({
                    'name': 'TestLead',
                    'contact_name': name,
                    'email_from': formatted_email,
                    'lang_id': lang.id,
                    'description': description,
                    'partner_name': partner_name,
                    **lead_details_for_contact,
                })
                data = lead1._message_get_suggested_recipients()[lead1.id]
                suggested_partner_id, suggested_partner_email, suggested_lang, suggested_reason, create_vals = data[0]
                self.assertFalse(suggested_partner_id)
                self.assertEqual(suggested_partner_email, formatted_email)
                self.assertEqual(suggested_lang, lang.code)
                self.assertEqual(suggested_reason, 'Customer Email')
                self.assertEqual(create_vals, lead1._get_customer_information().get(email, {}))
                for field, value in lead_details_for_contact.items():
                    self.assertEqual(create_vals.get(field), value)
                expected_name = partner_name if partner_name and not name else name
                self.assertEqual(create_vals['name'], expected_name)
                self.assertEqual(create_vals['comment'], description)  # description -> comment
                # Parent company not created even if partner_name is set
                self.assertFalse(create_vals.get('parent_id'))  # not supported, even if partner_name set
                self.assertEqual(create_vals['company_name'], partner_name)  # partner_name -> company_name
                expected_company_type = 'company' if partner_name and not name else 'person'
                self.assertEqual(create_vals.get('company_type', 'person'), expected_company_type)

                # Check that the creation of the contact won't fail
                partner = self.env['res.partner'].create(create_vals)
                partner.unlink()

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
To: sale_team_0@test.mycompany.com
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
To: sale_team_1@test.mycompany.com
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
