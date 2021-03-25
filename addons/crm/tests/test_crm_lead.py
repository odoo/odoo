# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.models.crm_lead import PARTNER_FIELDS_TO_SYNC, PARTNER_ADDRESS_FIELDS_TO_SYNC
from odoo.addons.crm.tests.common import TestCrmCommon, INCOMING_EMAIL
from odoo.addons.phone_validation.tools.phone_validation import phone_format
from odoo.tests.common import Form, users


class TestCRMLead(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestCRMLead, cls).setUpClass()
        cls.country_ref = cls.env.ref('base.be')
        cls.test_email = '"Test Email" <test.email@example.com>'
        cls.test_phone = '0485112233'

    def assertLeadAddress(self, lead, street, street2, city, lead_zip, state, country):
        self.assertEqual(lead.street, street)
        self.assertEqual(lead.street2, street2)
        self.assertEqual(lead.city, city)
        self.assertEqual(lead.zip, lead_zip)
        self.assertEqual(lead.state_id, state)
        self.assertEqual(lead.country_id, country)

    @users('user_sales_leads')
    def test_crm_lead_contact_fields_mixed(self):
        """ Test mixed configuration from partner: both user input and coming
        from partner, in order to ensure we do not loose information or make
        it incoherent. """
        lead_data = {
            'name': 'TestMixed',
            'partner_id': self.contact_1.id,
            # address
            'country_id': self.country_ref.id,
            # other contact fields
            'function': 'Parmesan Rappeur',
            # specific contact fields
            'email_from': self.test_email,
            'phone': self.test_phone,
        }
        lead = self.env['crm.lead'].create(lead_data)
        # classic
        self.assertEqual(lead.name, "TestMixed")
        # address
        self.assertLeadAddress(lead, False, False, False, False, self.env['res.country.state'], self.country_ref)
        # other contact fields
        for fname in set(PARTNER_FIELDS_TO_SYNC) - set(['function']):
            self.assertEqual(lead[fname], self.contact_1[fname], 'No user input -> take from contact for field %s' % fname)
        self.assertEqual(lead.function, 'Parmesan Rappeur', 'User input should take over partner value')
        # specific contact fields
        self.assertEqual(lead.partner_name, self.contact_company_1.name)
        self.assertEqual(lead.contact_name, self.contact_1.name)
        self.assertEqual(lead.email_from, self.test_email)
        self.assertEqual(lead.phone, self.test_phone)

        # update a single address fields -> only those are updated
        lead.write({'street': 'Super Street', 'city': 'Super City'})
        self.assertLeadAddress(lead, 'Super Street', False, 'Super City', False, self.env['res.country.state'], self.country_ref)

        # change partner -> whole address updated
        lead.write({'partner_id': self.contact_company_1.id})
        for fname in PARTNER_ADDRESS_FIELDS_TO_SYNC:
            self.assertEqual(lead[fname], self.contact_company_1[fname])

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

    def test_crm_lead_creation_partner_address(self):
        """ Test that an address erases all lead address fields (avoid mixed addresses) """
        other_country = self.env.ref('base.fr')
        empty_partner = self.env['res.partner'].create({
            'name': 'Empty partner',
            'country_id': other_country.id,
        })
        lead_data = {
            'name': 'Test',
            'street': 'My street',
            'street2': 'My street',
            'city': 'My city',
            'zip': 'test@odoo.com',
            'state_id': self.env['res.country.state'].create({
                'name': 'My state',
                'country_id': self.country_ref.id,
                'code': 'MST',
            }).id,
            'country_id': self.country_ref.id,
        }
        lead = self.env['crm.lead'].create(lead_data)
        lead.partner_id = empty_partner
        # PARTNER_ADDRESS_FIELDS_TO_SYNC
        self.assertEqual(lead.street, empty_partner.street, "Street should be sync from the Partner")
        self.assertEqual(lead.street2, empty_partner.street2, "Street 2 should be sync from the Partner")
        self.assertEqual(lead.city, empty_partner.city, "City should be sync from the Partner")
        self.assertEqual(lead.zip, empty_partner.zip, "Zip should be sync from the Partner")
        self.assertEqual(lead.state_id, empty_partner.state_id, "State should be sync from the Partner")
        self.assertEqual(lead.country_id, empty_partner.country_id, "Country should be sync from the Partner")

    def test_crm_lead_creation_partner_no_address(self):
        """ Test that an empty address on partner does not void its lead values """
        empty_partner = self.env['res.partner'].create({
            'name': 'Empty partner',
            'is_company': True,
            'mobile': '123456789',
            'title': self.env.ref('base.res_partner_title_mister').id,
            'function': 'My function',
        })
        lead_data = {
            'name': 'Test',
            'contact_name': 'Test',
            'street': 'My street',
            'country_id': self.country_ref.id,
            'email_from': self.test_email,
            'phone': self.test_phone,
            'mobile': '987654321',
            'website': 'http://mywebsite.org',
        }
        lead = self.env['crm.lead'].create(lead_data)
        lead.partner_id = empty_partner
        # SPECIFIC FIELDS
        self.assertEqual(lead.contact_name, lead_data['contact_name'], "Contact should remain")
        self.assertEqual(lead.email_from, lead_data['email_from'], "Email From should keep its initial value")
        self.assertEqual(lead.partner_name, empty_partner.name, "Partner name should be set as contact is a company")
        # PARTNER_ADDRESS_FIELDS_TO_SYNC
        self.assertEqual(lead.street, lead_data['street'], "Street should remain since partner has no address field set")
        self.assertEqual(lead.street2, False, "Street2 should remain since partner has no address field set")
        self.assertEqual(lead.country_id, self.country_ref, "Country should remain since partner has no address field set")
        self.assertEqual(lead.city, False, "City should remain since partner has no address field set")
        self.assertEqual(lead.zip, False, "Zip should remain since partner has no address field set")
        self.assertEqual(lead.state_id, self.env['res.country.state'], "State should remain since partner has no address field set")
        # PARTNER_FIELDS_TO_SYNC
        self.assertEqual(lead.phone, lead_data['phone'], "Phone should keep its initial value")
        self.assertEqual(lead.mobile, empty_partner.mobile, "Mobile from partner should be set on the lead")
        self.assertEqual(lead.title, empty_partner.title, "Title from partner should be set on the lead")
        self.assertEqual(lead.function, empty_partner.function, "Function from partner should be set on the lead")
        self.assertEqual(lead.website, lead_data['website'], "Website should keep its initial value")

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
    def test_crm_lead_partner_sync_email_phone(self):
        """ Specifically test synchronize between a lead and its partner about
        phone and email fields. Phone especially has some corner cases due to
        automatic formatting (notably with onchange in form view). """
        lead, partner = self.lead_1.with_user(self.env.user), self.contact_2
        lead_form = Form(lead)

        # reset partner phone to a local number and prepare formatted / sanitized values
        partner_phone, partner_mobile = self.test_pĥone_data[2], self.test_pĥone_data[1]
        partner_phone_formatted = phone_format(partner_phone, 'US', '1')
        partner_phone_sanitized = phone_format(partner_phone, 'US', '1', force_format='E164')
        partner_mobile_formatted = phone_format(partner_mobile, 'US', '1')
        partner_mobile_sanitized = phone_format(partner_mobile, 'US', '1', force_format='E164')
        partner_email, partner_email_normalized = self.test_email_data[2], self.test_email_data_normalized[2]
        self.assertEqual(partner_phone_formatted, '+1 202-555-0888')
        self.assertEqual(partner_phone_sanitized, self.test_pĥone_data_sanitized[2])
        self.assertEqual(partner_mobile_formatted, '+1 202-555-0999')
        self.assertEqual(partner_mobile_sanitized, self.test_pĥone_data_sanitized[1])
        # ensure initial data
        self.assertEqual(partner.phone, partner_phone)
        self.assertEqual(partner.mobile, partner_mobile)
        self.assertEqual(partner.email, partner_email)

        # LEAD/PARTNER SYNC: email and phone are propagated to lead
        # as well as mobile (who does not trigger the reverse sync)
        lead_form.partner_id = partner
        self.assertEqual(lead_form.email_from, partner_email)
        self.assertEqual(lead_form.phone, partner_phone_formatted,
                         'Lead: form automatically formats numbers')
        self.assertEqual(lead_form.mobile, partner_mobile_formatted,
                         'Lead: form automatically formats numbers')
        self.assertFalse(lead_form.ribbon_message)

        lead_form.save()
        self.assertEqual(partner.phone, partner_phone,
                         'Lead / Partner: partner values sent to lead')
        self.assertEqual(lead.email_from, partner_email,
                         'Lead / Partner: partner values sent to lead')
        self.assertEqual(lead.email_normalized, partner_email_normalized,
                         'Lead / Partner: equal emails should lead to equal normalized emails')
        self.assertEqual(lead.phone, partner_phone_formatted,
                         'Lead / Partner: partner values (formatted) sent to lead')
        self.assertEqual(lead.mobile, partner_mobile_formatted,
                         'Lead / Partner: partner values (formatted) sent to lead')
        self.assertEqual(lead.phone_sanitized, partner_mobile_sanitized,
                         'Lead: phone_sanitized computed field on mobile')

        # for email_from, if only formatting differs, warning ribbon should
        # not appear and email on partner should not be updated
        lead_form.email_from = '"Hermes Conrad" <%s>' % partner_email_normalized
        self.assertFalse(lead_form.ribbon_message)
        lead_form.save()
        self.assertEqual(lead_form.partner_id.email, partner_email)

        # LEAD/PARTNER SYNC: lead updates partner
        new_email = '"John Zoidberg" <john.zoidberg@test.example.com>'
        new_email_normalized = 'john.zoidberg@test.example.com'
        lead_form.email_from = new_email
        self.assertIn('the customer email will', lead_form.ribbon_message)
        new_phone = '+1 202 555 7799'
        new_phone_formatted = phone_format(new_phone, 'US', '1')
        lead_form.phone = new_phone
        self.assertEqual(lead_form.phone, new_phone_formatted)
        self.assertIn('the customer email and phone number will', lead_form.ribbon_message)

        lead_form.save()
        self.assertEqual(partner.email, new_email)
        self.assertEqual(partner.email_normalized, new_email_normalized)
        self.assertEqual(partner.phone, new_phone_formatted)

        # LEAD/PARTNER SYNC: mobile does not update partner
        new_mobile = '+1 202 555 6543'
        new_mobile_formatted = phone_format(new_mobile, 'US', '1')
        lead_form.mobile = new_mobile
        lead_form.save()
        self.assertEqual(lead.mobile, new_mobile_formatted)
        self.assertEqual(partner.mobile, partner_mobile)

        # LEAD/PARTNER SYNC: reseting lead values also resets partner for email
        # and phone, but not for mobile
        lead_form.email_from, lead_form.phone, lead.mobile = False, False, False
        self.assertIn('the customer email and phone number will', lead_form.ribbon_message)
        lead_form.save()
        self.assertFalse(partner.email)
        self.assertFalse(partner.email_normalized)
        self.assertFalse(partner.phone)
        self.assertFalse(lead.phone)
        self.assertFalse(lead.mobile)
        self.assertFalse(lead.phone_sanitized)
        self.assertEqual(partner.mobile, partner_mobile)
        self.assertEqual(partner.phone_sanitized, partner_mobile_sanitized,
                         'Partner sanitized should be computed on mobile')

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
