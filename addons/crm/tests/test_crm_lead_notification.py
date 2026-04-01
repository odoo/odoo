# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import INCOMING_EMAIL, TestCrmCommon
from odoo.tests import tagged, users
from odoo.tools import email_normalize, formataddr, mute_logger


@tagged('mail_thread', 'mail_gateway')
class NewLeadNotification(TestCrmCommon):
    """ Test mail features support on lead + specific overrides and support """

    @classmethod
    def setUpClass(cls):
        """ Activate some langs to test lang propagation in various mail flows """
        super(NewLeadNotification, cls).setUpClass()
        cls._activate_multi_company()

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
    def test_lead_message_get_suggested_recipients(self):
        """ Test '_message_get_suggested_recipients' and its override in lead
        when dealing with various emails. """
        self.maxDiff = None  # to ease assertDictEqual usage
        company_partner = self.env['res.partner'].create(
            {'name': 'test_lead_message_get_suggested_recipients_company_partner', 'is_company': True}
        )
        partner_no_email = self.env['res.partner'].create({'name': 'Test Partner', 'email': False})
        leads = self.env['crm.lead'].create([
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
                'email_from': 'new.customer.with.parent@test.example.com',
                'name': 'Test Suggestion (email_from with matching partner_name)',
                'partner_name': 'test_lead_message_get_suggested_recipients_company_partner',
                'user_id': self.user_sales_leads.id,
            }, {
                'email_from': 'new.customer.simple@test.example.com',
                'name': 'Test Suggestion (email_from)',
                'contact_name': 'Std Name',
                'user_id': self.user_sales_leads.id,
            }, {
                'email_from': 'test.lang@test.example.com',
                'lang_id': self.lang_en.id,
                'name': 'Test Suggestion (lang)',
                'user_id': False,
            }, {
                'name': 'Test Suggestion (partner_id)',
                'partner_id': self.contact_1.id,
                'user_id': self.user_sales_leads.id,
            }, {
                'name': 'Test Suggestion (partner no email)',
                'partner_id': partner_no_email.id,
                'user_id': self.user_sales_leads.id
            }, {
                'name': 'Test Suggestion (partner no email with cc email)',
                'partner_id': partner_no_email.id,
                'email_cc': 'test_cc@odoo.com',
                'user_id': self.user_sales_leads.id
            }
        ])
        for lead, expected_suggested in zip(leads, [
            [
                # here contact_name is guessed based on formatted email
                {
                    'name': 'New Customer',
                    'email': 'new.customer.format@test.example.com',
                    'partner_id': False,
                    'create_values': {
                        'company_name': 'Format Name',
                        'is_company': False,
                        'type': 'contact',
                        'user_id': self.user_sales_leads.id,
                    },
                },
            ], [
                # here no contact name, just a partner name -> use email and set company_name
                {
                    'name': 'new.customer.multi.1@test.example.com, new.customer.2@test.example.com',
                    'email': 'new.customer.multi.1@test.example.com',  # only first found normalized email is kept
                    'partner_id': False,
                    'create_values': {
                        'company_name': 'Multi Name',
                        'is_company': False,
                        'type': 'contact',
                        'user_id': self.user_sales_leads.id,
                    },
                }, {
                    'name': '',
                    'email': 'new.customer.2@test.example.com',  # second found creates another contact
                    'partner_id': False,
                    'create_values': {},  # not targeted as primary lead customer hence no values
                },
            ], [
                # here no contact name, a partner name, but there exists a company with that name -> company
                {
                    'name': 'new.customer.with.parent@test.example.com',
                    'email': 'new.customer.with.parent@test.example.com',
                    'partner_id': False,
                    'create_values': {
                        'is_company': False,
                        'parent_id': company_partner.id,
                        'type': 'contact',
                        'user_id': self.user_sales_leads.id,
                    },
                },
            ], [
                # here contact name -> individual
                {
                    'name': 'Std Name',
                    'email': 'new.customer.simple@test.example.com',
                    'partner_id': False,
                    'create_values': {
                        'is_company': False,
                        'type': 'contact',
                        'user_id': self.user_sales_leads.id,
                    },
                },
            ], [
                # here check lang is in create_values
                {
                    'name': 'test.lang@test.example.com',
                    'email': 'test.lang@test.example.com',
                    'partner_id': False,
                    'create_values': {
                        'is_company': False,
                        'lang': 'en_US',
                        'type': 'contact',
                    },
                },
            ], [
                {
                    'partner_id': self.contact_1.id,
                    'name': 'Philip J Fry',
                    'email': 'philip.j.fry@test.example.com',
                    'create_values': {},
                },
            ], [
                {
                    'partner_id': partner_no_email.id,
                    'name': 'Test Partner',
                    'email': False,
                    'create_values': {},
                },
            ], [
                {
                    'partner_id': partner_no_email.id,
                    'email': False,
                    'name': 'Test Partner',
                    'create_values': {},
                }, {
                    'name': '',
                    'email': 'test_cc@odoo.com',
                    'partner_id': False,
                    'create_values': {},
                },
            ],
        ]):
            with self.subTest(lead_name=lead.name, email_from=lead.email_from):
                res = lead._message_get_suggested_recipients(no_create=True)
                self.assertEqual(len(res), len(expected_suggested))
                for received, expected in zip(res, expected_suggested):
                    self.assertDictEqual(received, expected)

    @users('user_sales_manager')
    def test_lead_message_get_suggested_recipients_values_for_create(self):
        """Check default creates value used when creating client from suggested
        recipients (customer)."""
        lead_details_for_contact = {
            'street': '3rd Floor, Room 3-C',
            'street2': '123 Arlington Avenue',
            'zip': '13202',
            'city': 'New York',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
            'website': 'https://www.arlington123.com/3f3c',
            'phone': '678-728-0949',
            'function': 'Delivery Boy',
            'user_id': self.user_sales_manager.id,
        }

        for partner_name, contact_name, email in [
            (False, 'ContactOnly', 'test_default_create@example.com'),
            ('Delivery Boy company', 'ContactAndCompany', 'default_create_with_partner@example.com'),
            ('Delivery Boy company', '', '"Contact Name" <default_create_with_name_in_email@example.com>'),
            ('Delivery Boy company', '', 'default_create_with_partner_no_name@example.com'),
            ('', '', 'lenny.bar@gmail.com'),
        ]:
            if email == '"Contact Name" <default_create_with_name_in_email@example.com>':
                suggested_email = 'default_create_with_name_in_email@example.com'
                suggested_name = "Contact Name"
            else:
                suggested_email = email
                # if no contact_name: fallback on the email to at least have something
                suggested_name = contact_name or email
            with self.subTest(partner_name=partner_name, contact_name=contact_name, email=email):
                description = '<p>Top</p>'
                lead1 = self.env['crm.lead'].create({
                    'name': 'TestLead',
                    'contact_name': contact_name,
                    'email_from': email,
                    'lang_id': self.lang_en.id,
                    'description': description,
                    'partner_name': partner_name,
                    **lead_details_for_contact,
                })
                suggestion = lead1._message_get_suggested_recipients(no_create=True)[0]
                self.assertFalse(suggestion.get('partner_id'))
                self.assertEqual(suggestion['email'], suggested_email)
                self.assertEqual(suggestion['name'], suggested_name)

                create_values = suggestion['create_values']
                customer_information = lead1._get_customer_information().get(email_normalize(email), {})
                customer_information.pop('name', False)  # not keps in create_values, as already in name / email info
                self.assertEqual(create_values, customer_information)
                for field, value in lead_details_for_contact.items():
                    self.assertEqual(create_values.get(field), value)
                self.assertEqual(create_values['comment'], description)  # description -> comment
                # parent company not created even if partner_name is set
                self.assertFalse(create_values.get('parent_id'))  # not supported, even if partner_name set
                # company_name set only for contacts with partner_name (and no contact_name nor name in email)
                if partner_name:
                    self.assertEqual(create_values['company_name'], partner_name)  # partner_name -> company_name
                else:
                    self.assertFalse('company_name' in create_values)
                # it will normally never be a company, unless called despite a contact being already present (shouldn't happen)
                self.assertEqual(create_values['is_company'], False)

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
        company1 = self.company_2

        self.env.user.write({
            'company_ids': [(4, company0.id, False), (4, company1.id, False)],
        })

        crm_team_model_id = self.env['ir.model']._get_id('crm.team')
        crm_lead_model_id = self.env['ir.model']._get_id('crm.lead')

        crm_team0 = self.env['crm.team'].create({
            'name': 'crm team 0',
            'company_id': company0.id,
        })
        crm_team1 = self.env['crm.team'].create({
            'name': 'crm team 1',
            'company_id': company1.id,
        })

        mail_alias0 = self.env['mail.alias'].create({
            'alias_domain_id': company0.alias_domain_id.id,
            'alias_name': 'sale_team_0',
            'alias_model_id': crm_lead_model_id,
            'alias_parent_model_id': crm_team_model_id,
            'alias_parent_thread_id': crm_team0.id,
            'alias_defaults': "{'type': 'opportunity', 'team_id': %s}" % crm_team0.id,
        })
        mail_alias1 = self.env['mail.alias'].create({
            'alias_domain_id': company1.alias_domain_id.id,
            'alias_name': 'sale_team_1',
            'alias_model_id': crm_lead_model_id,
            'alias_parent_model_id': crm_team_model_id,
            'alias_parent_thread_id': crm_team1.id,
            'alias_defaults': "{'type': 'opportunity', 'team_id': %s}" % crm_team1.id,
        })

        crm_team0.write({'alias_id': mail_alias0.id})
        crm_team1.write({'alias_id': mail_alias1.id})

        new_message0 = f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: <blablabla0>
Subject: sale team 0 in company 0
From:  A client <client_a@someprovider.com>
To: {mail_alias0.display_name}
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message</div>

--000000000000a47519057e029630--
"""

        new_message1 = f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: <blablabla1>
Subject: sale team 1 in company 1
From:  B client <client_b@someprovider.com>
To: {mail_alias1.display_name}
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

    @users('user_sales_manager')
    def test_incoming_email_automatic_lead_assignment(self):
        # create a second team with a set leader
        leader_team_2 = self.env['res.users'].sudo().create({'name': 'bob', 'login': 'bob'})
        team_2 = self.env['crm.team'].create({
            'name': 'team_2',
            'alias_name': 'team.2',
            'user_id': leader_team_2.id,
        })

        # send three emails to the aliases of both teams
        for x in range(3):
            self.format_and_process(
                INCOMING_EMAIL,
                f'source.email@customerOfTeam1{x}.be',
                self.sales_team_1.alias_email,
                subject=f'OpportunityTeam1{x}',
                target_model='crm.lead',
            )
            self.format_and_process(
                INCOMING_EMAIL,
                f'source.email@customerOfTeam2{x}.be',
                team_2.alias_email,
                subject=f'OpportunityTeam2{x}',
                target_model='crm.lead',
            )

        # each team should receive all three of their new opportunities and none of the others'
        team1_leads = self.env['crm.lead'].search([
            ('team_id', '=', self.sales_team_1.id),
            ('email_from', 'ilike', 'source.email@customerOfTeam'),
        ])
        team2_leads = self.env['crm.lead'].search([
            ('team_id', '=', team_2.id),
            ('email_from', 'ilike', 'source.email@customerOfTeam'),
        ])
        for lead in team1_leads:
            self.assertTrue('source.email@customerOfTeam1' in lead.email_from)
            self.assertTrue(lead.user_id == self.user_sales_manager)
        for lead in team2_leads:
            self.assertTrue('source.email@customerOfTeam2' in lead.email_from)
            self.assertTrue(lead.user_id == leader_team_2)
