# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon, INCOMING_EMAIL
from odoo.tests.common import users


class TestCRMLead(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestCRMLead, cls).setUpClass()
        cls.country_ref = cls.env.ref('base.be')
        cls.test_email = '"Test Email" <test.email@example.com>'
        cls.test_phone = '0485112233'

    @users('user_sales_leads')
    def test_crm_lead_creation_no_partner(self):
        lead_data = {
            'name': 'Test',
            'country_id': self.country_ref.id,
            'email_from': self.test_email,
            'phone': self.test_phone,
        }
        lead = self.env['crm.lead'].new(lead_data)
        # get the street should not trigger cache miss
        lead.street
        # Create the lead and the write partner_id = False: country should remain
        lead = self.env['crm.lead'].create(lead_data)
        self.assertEqual(lead.country_id, self.country_ref, "Country should be set on the lead")
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead.phone, self.test_phone)
        lead.partner_id = False
        self.assertEqual(lead.country_id, self.country_ref, "Country should still be set on the lead")
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead.phone, self.test_phone)

    @users('user_sales_manager')
    def test_crm_lead_creation_partner(self):
        lead = self.env['crm.lead'].create({
            'name': 'TestLead',
            'contact_name': 'Raoulette TestContact',
            'email_from': '"Raoulette TestContact" <raoulette@test.example.com>',
        })
        self.assertEqual(lead.type, 'lead')
        self.assertEqual(lead.user_id, self.user_sales_manager)
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)
        self.assertEqual(lead.contact_name, 'Raoulette TestContact')
        self.assertEqual(lead.email_from, '"Raoulette TestContact" <raoulette@test.example.com>')

        # update to a partner, should udpate address
        lead.write({'partner_id': self.contact_1.id})
        self.assertEqual(lead.partner_name, self.contact_company_1.name)
        self.assertEqual(lead.contact_name, self.contact_1.name)
        self.assertEqual(lead.email_from, self.contact_1.email)
        self.assertEqual(lead.street, self.contact_1.street)
        self.assertEqual(lead.city, self.contact_1.city)
        self.assertEqual(lead.zip, self.contact_1.zip)
        self.assertEqual(lead.country_id, self.contact_1.country_id)

    def test_crm_lead_creation_partner_no_info(self):
        empty_partner = self.env['res.partner'].create({
            'name': 'Empty partner',
            'is_company': True
        })
        lead_data = {
            'name': 'Test',
            'country_id': self.country_ref.id,
            'email_from': self.test_email,
            'phone': self.test_phone,
        }
        lead = self.env['crm.lead'].create(lead_data)
        lead.partner_id = empty_partner
        self.assertEqual(lead.country_id, self.env['res.country'], "Country should be empty")
        self.assertEqual(lead.contact_name, False, "Contact name should be empty")
        self.assertEqual(lead.email_from, self.test_email, "Email From should keep its initial value")
        self.assertEqual(lead.phone, self.test_phone, "Phone should keep its initial value")
        self.assertEqual(lead.partner_name, empty_partner.name, "Partner name should be set as contact is a company")

    @users('user_sales_manager')
    def test_crm_lead_partner_sync(self):
        lead, partner = self.lead_1.with_user(self.env.user), self.contact_2
        partner_email, partner_phone = self.contact_2.email, self.contact_2.phone
        lead.partner_id = partner

        # email & phone must be automatically set on the lead
        lead.partner_id = partner
        self.assertEqual(lead.email_from, partner_email)
        self.assertEqual(lead.phone, partner_phone)

        # writing on the lead field must change the partner field
        lead.email_from = '"John Zoidberg" <john.zoidberg@test.example.com>'
        lead.phone = '+1 202 555 7799'
        self.assertEqual(partner.email, '"John Zoidberg" <john.zoidberg@test.example.com>')
        self.assertEqual(partner.email_normalized, 'john.zoidberg@test.example.com')
        self.assertEqual(partner.phone, '+1 202 555 7799')

        # writing on the partner must change the lead values
        partner.email = partner_email
        partner.phone = '+1 202 555 6666'
        self.assertEqual(lead.email_from, partner_email)
        self.assertEqual(lead.phone, '+1 202 555 6666')

        # resetting lead values also resets partner
        lead.email_from, lead.phone = False, False
        self.assertFalse(partner.email)
        self.assertFalse(partner.email_normalized)
        self.assertFalse(partner.phone)

    @users('user_sales_manager')
    def test_crm_lead_stages(self):
        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.team_id, self.sales_team_1)

        lead.convert_opportunity(self.contact_1.id)
        self.assertEqual(lead.team_id, self.sales_team_1)

        lead.action_set_won()
        self.assertEqual(lead.probability, 100.0)
        self.assertEqual(lead.stage_id, self.stage_gen_won)  # generic won stage has lower sequence than team won stage

    @users('user_sales_leads')
    def test_crm_lead_update_contact(self):
        # ensure initial data, especially for corner cases
        self.assertFalse(self.contact_company_1.phone)
        self.assertEqual(self.contact_company_1.country_id.code, "US")
        lead = self.env['crm.lead'].create({
            'name': 'Test',
            'country_id': self.country_ref.id,
            'email_from': self.test_email,
            'phone': self.test_phone,
        })
        self.assertEqual(lead.country_id, self.country_ref, "Country should be set on the lead")
        lead.partner_id = False
        self.assertEqual(lead.country_id, self.country_ref, "Country should still be set on the lead")
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead.phone, self.test_phone)
        self.assertEqual(lead.email_state, 'correct')
        self.assertEqual(lead.phone_state, 'correct')

        lead.partner_id = self.contact_company_1
        self.assertEqual(lead.country_id, self.contact_company_1.country_id, "Country should still be the one set on partner")
        self.assertEqual(lead.email_from, self.contact_company_1.email)
        self.assertEqual(lead.phone, self.test_phone)
        self.assertEqual(lead.email_state, 'correct')
        # currently we keep phone as partner as a void one -> may lead to inconsistencies
        self.assertEqual(lead.phone_state, 'incorrect', "Belgian phone with US country -> considered as incorrect")

        lead.email_from = 'broken'
        lead.phone = 'alsobroken'
        self.assertEqual(lead.email_state, 'incorrect')
        self.assertEqual(lead.phone_state, 'incorrect')
        self.assertEqual(self.contact_company_1.email, 'broken')
        self.assertEqual(self.contact_company_1.phone, 'alsobroken')

    @users('user_sales_manager')
    def test_crm_team_alias(self):
        new_team = self.env['crm.team'].create({
            'name': 'TestAlias',
            'use_leads': True,
            'use_opportunities': True,
            'alias_name': 'test.alias'
        })
        self.assertEqual(new_team.alias_id.alias_name, 'test.alias')
        self.assertEqual(new_team.alias_name, 'test.alias')

        new_team.write({
            'use_leads': False,
            'use_opportunities': False,
        })
        # self.assertFalse(new_team.alias_id.alias_name)
        # self.assertFalse(new_team.alias_name)

    def test_mailgateway(self):
        new_lead = self.format_and_process(
            INCOMING_EMAIL,
            'unknown.sender@test.example.com',
            '%s@%s' % (self.sales_team_1.alias_name, self.alias_domain),
            subject='Delivery cost inquiry',
            target_model='crm.lead',
        )
        self.assertEqual(new_lead.email_from, 'unknown.sender@test.example.com')
        self.assertFalse(new_lead.partner_id)
        self.assertEqual(new_lead.name, 'Delivery cost inquiry')

        message = new_lead.with_user(self.user_sales_manager).message_post(
            body='Here is my offer !',
            subtype_xmlid='mail.mt_comment')
        self.assertEqual(message.author_id, self.user_sales_manager.partner_id)

        new_lead.handle_partner_assignment(create_missing=True)
        self.assertEqual(new_lead.partner_id.email, 'unknown.sender@test.example.com')
        self.assertEqual(new_lead.partner_id.team_id, self.sales_team_1)
