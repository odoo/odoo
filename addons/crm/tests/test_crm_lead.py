# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo import fields
from odoo.addons.base.tests.test_format_address_mixin import FormatAddressCase
from odoo.addons.crm.models.crm_lead import PARTNER_FIELDS_TO_SYNC, PARTNER_ADDRESS_FIELDS_TO_SYNC
from odoo.addons.crm.tests.common import TestCrmCommon, INCOMING_EMAIL
from odoo.addons.mail.tests.mail_tracking_duration_mixin_case import MailTrackingDurationMixinCase
from odoo.addons.phone_validation.tools.phone_validation import phone_format
from odoo.exceptions import UserError
from odoo.tests.common import Form, tagged, users
from odoo.tools import mute_logger


@tagged('lead_internals')
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
            'lang_id': self.lang_fr.id,
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
        for fname in set(PARTNER_FIELDS_TO_SYNC) - set(['function', 'lang']):
            self.assertEqual(lead[fname], self.contact_1[fname], 'No user input -> take from contact for field %s' % fname)
        self.assertEqual(lead.function, 'Parmesan Rappeur', 'User input should take over partner value')
        self.assertEqual(lead.lang_id, self.lang_fr)
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
            self.assertEqual(self.contact_company_1.lang, self.lang_en.code)
            self.assertEqual(lead.lang_id, self.lang_en)

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
        self.assertEqual(self.contact_1.lang, self.env.user.lang)

        # update to a partner, should udpate address
        lead.write({'partner_id': self.contact_1.id})
        self.assertEqual(lead.partner_name, self.contact_company_1.name)
        self.assertEqual(lead.contact_name, self.contact_1.name)
        self.assertEqual(lead.email_from, self.contact_1.email)
        self.assertEqual(lead.street, self.contact_1.street)
        self.assertEqual(lead.city, self.contact_1.city)
        self.assertEqual(lead.zip, self.contact_1.zip)
        self.assertEqual(lead.country_id, self.contact_1.country_id)
        self.assertEqual(lead.lang_id.code, self.contact_1.lang)

    @users('user_sales_manager')
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

    @users('user_sales_manager')
    def test_crm_lead_creation_partner_company(self):
        """ Test lead / partner synchronization involving company details """
        # Test that partner_name (company name) is the partner name if partner is company
        lead = self.env['crm.lead'].create({
            'name': 'TestLead',
            'partner_id': self.contact_company.id,
        })
        self.assertEqual(lead.contact_name, False,
                         "Lead contact name should be Falsy when dealing with companies")
        self.assertEqual(lead.partner_name, self.contact_company.name,
                         "Lead company name should be set to partner name if partner is a company")
        # Test that partner_name (company name) is the partner company name if partner is an individual
        self.contact_company.write({'is_company': False})
        lead = self.env['crm.lead'].create({
            'name': 'TestLead',
            'partner_id': self.contact_company.id,
        })
        self.assertEqual(lead.contact_name, self.contact_company.name,
                         "Lead contact name should be set to partner name if partner is not a company")
        self.assertEqual(lead.partner_name, self.contact_company.company_name,
                         "Lead company name should be set to company name if partner is not a company")

    @users('user_sales_manager')
    def test_crm_lead_creation_partner_no_address(self):
        """ Test that an empty address on partner does not void its lead values """
        empty_partner = self.env['res.partner'].create({
            'name': 'Empty partner',
            'is_company': True,
            'lang': 'en_US',
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
        self.assertEqual(lead.lang_id, self.lang_en)
        self.assertEqual(lead.phone, lead_data['phone'], "Phone should keep its initial value")
        self.assertEqual(lead.mobile, empty_partner.mobile, "Mobile from partner should be set on the lead")
        self.assertEqual(lead.title, empty_partner.title, "Title from partner should be set on the lead")
        self.assertEqual(lead.function, empty_partner.function, "Function from partner should be set on the lead")
        self.assertEqual(lead.website, lead_data['website'], "Website should keep its initial value")

    @users('user_sales_manager')
    def test_crm_lead_create_pipe_data(self):
        """ Test creation pipe data: user, team, stage, depending on some default
        configuration. """
        # gateway-like creation: no user, no team, generic stage
        lead = self.env['crm.lead'].with_context(default_user_id=False).create({
            'name': 'Test',
            'contact_name': 'Test Contact',
            'email_from': self.test_email,
            'phone': self.test_phone,
        })
        self.assertEqual(lead.user_id, self.env['res.users'])
        self.assertEqual(lead.team_id, self.env['crm.team'])
        self.assertEqual(lead.stage_id, self.stage_gen_1)

        # pipe creation: current user's best team and default stage
        lead = self.env['crm.lead'].create({
            'name': 'Test',
            'contact_name': 'Test Contact',
            'email_from': self.test_email,
            'phone': self.test_phone,
        })
        self.assertEqual(lead.user_id, self.user_sales_manager)
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)

    @users('user_sales_manager')
    def test_crm_lead_currency_sync(self):
        lead_company = self.env['res.company'].sudo().create({
            'name': 'EUR company',
            'currency_id': self.env.ref('base.EUR').id,
        })
        lead = self.env['crm.lead'].with_company(lead_company).create({
            'name': 'Lead 1',
            'company_id': lead_company.id
        })
        self.assertEqual(lead.company_currency, self.env.ref('base.EUR'))

        lead_company.currency_id = self.env.ref('base.CHF')
        lead.update({'company_id': False})
        self.assertEqual(lead.company_currency, self.env.ref('base.CHF'))

    @users('user_sales_manager')
    def test_crm_lead_date_closed(self):
        # Test for one won lead
        stage_team1_won2 = self.env['crm.stage'].create({
            'name': 'Won2',
            'sequence': 75,
            'team_id': self.sales_team_1.id,
            'is_won': True,
        })
        won_lead = self.lead_team_1_won.with_env(self.env)
        other_lead = self.lead_1.with_env(self.env)
        old_date_closed = won_lead.date_closed
        self.assertTrue(won_lead.date_closed)
        self.assertFalse(other_lead.date_closed)

        # multi update
        leads = won_lead + other_lead
        with freeze_time('2020-02-02 18:00'):
            leads.stage_id = stage_team1_won2
        self.assertEqual(won_lead.date_closed, old_date_closed, 'Should not change date')
        self.assertEqual(other_lead.date_closed, datetime(2020, 2, 2, 18, 0, 0))

        # back to open stage
        leads.write({'stage_id': self.stage_team1_2.id})
        self.assertFalse(won_lead.date_closed)
        self.assertFalse(other_lead.date_closed)

        # close with lost
        with freeze_time('2020-02-02 18:00'):
            leads.action_set_lost()
        self.assertEqual(won_lead.date_closed, datetime(2020, 2, 2, 18, 0, 0))
        self.assertEqual(other_lead.date_closed, datetime(2020, 2, 2, 18, 0, 0))

    @users('user_sales_leads')
    @freeze_time("2012-01-14")
    def test_crm_lead_lost_date_closed(self):
        lead = self.lead_1.with_env(self.env)
        self.assertFalse(lead.date_closed, "Initially, closed date is not set")
        # Mark the lead as lost
        lead.action_set_lost()
        self.assertEqual(lead.date_closed, datetime.now(), "Closed date is updated after marking lead as lost")

    @users('user_sales_manager')
    def test_crm_lead_meeting_display_fields(self):
        lead = self.env['crm.lead'].create({'name': 'Lead With Meetings'})
        meeting_1, meeting_2, meeting_3 = self.env['calendar.event'].create([{
            'name': 'Meeting 1 of Lead',
            'opportunity_id': lead.id,
            'start': '2022-07-12 08:00:00',
            'stop': '2022-07-12 10:00:00',
        }, {
            'name': 'Meeting 2 of Lead',
            'opportunity_id': lead.id,
            'start': '2022-07-14 08:00:00',
            'stop': '2022-07-14 10:00:00',
        }, {
            'name': 'Meeting 3 of Lead',
            'opportunity_id': lead.id,
            'start': '2022-07-15 08:00:00',
            'stop': '2022-07-15 10:00:00',
        }])

        with freeze_time('2022-07-13 11:00:00'):
            self.assertEqual(lead.meeting_display_date, fields.Date.from_string('2022-07-14'))
            self.assertEqual(lead.meeting_display_label, 'Next Meeting')
            (meeting_2 | meeting_3).unlink()
            self.assertEqual(lead.meeting_display_date, fields.Date.from_string('2022-07-12'))
            self.assertEqual(lead.meeting_display_label, 'Last Meeting')
            meeting_1.unlink()
            self.assertFalse(lead.meeting_display_date)
            self.assertEqual(lead.meeting_display_label, 'No Meeting')

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
        # This is a type == 'lead', not a type == 'opportunity'
        # {'invisible': ['|', ('type', '=', 'opportunity'), ('is_partner_visible', '=', False)]}
        # lead.is_partner_visible = bool(lead.type == 'opportunity' or lead.partner_id or is_debug_mode)
        # Hence, debug mode required for `partner_id` to be visible
        with self.debug_mode():
            lead_form = Form(lead)

            # reset partner phone to a local number and prepare formatted / sanitized values
            partner_phone, partner_mobile = self.test_phone_data[2], self.test_phone_data[1]
            partner_phone_formatted = phone_format(partner_phone, 'US', '1', force_format='INTERNATIONAL')
            partner_phone_sanitized = phone_format(partner_phone, 'US', '1', force_format='E164')
            partner_mobile_formatted = phone_format(partner_mobile, 'US', '1', force_format='INTERNATIONAL')
            partner_mobile_sanitized = phone_format(partner_mobile, 'US', '1', force_format='E164')
            partner_email, partner_email_normalized = self.test_email_data[2], self.test_email_data_normalized[2]
            self.assertEqual(partner_phone_formatted, '+1 202-555-0888')
            self.assertEqual(partner_phone_sanitized, self.test_phone_data_sanitized[2])
            self.assertEqual(partner_mobile_formatted, '+1 202-555-0999')
            self.assertEqual(partner_mobile_sanitized, self.test_phone_data_sanitized[1])
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
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)

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

            # for email_from, if only formatting differs, warning should not appear and
            # email on partner should not be updated
            lead_form.email_from = '"Hermes Conrad" <%s>' % partner_email_normalized
            self.assertFalse(lead_form.partner_email_update)
            lead_form.save()
            self.assertEqual(partner.email, partner_email)

            # for phone, if only formatting differs, warning should not appear and
            # phone on partner should not be updated
            lead_form.phone = partner_phone_sanitized
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.save()
            self.assertEqual(partner.phone, partner_phone)

            # LEAD/PARTNER SYNC: lead updates partner
            new_email = '"John Zoidberg" <john.zoidberg@test.example.com>'
            new_email_normalized = 'john.zoidberg@test.example.com'
            lead_form.email_from = new_email
            self.assertTrue(lead_form.partner_email_update)
            new_phone = '+1 202 555 7799'
            new_phone_formatted = phone_format(new_phone, 'US', '1', force_format="INTERNATIONAL")
            lead_form.phone = new_phone
            self.assertEqual(lead_form.phone, new_phone_formatted)
            self.assertTrue(lead_form.partner_email_update)
            self.assertTrue(lead_form.partner_phone_update)

            lead_form.save()
            self.assertEqual(partner.email, new_email)
            self.assertEqual(partner.email_normalized, new_email_normalized)
            self.assertEqual(partner.phone, new_phone_formatted)

            # LEAD/PARTNER SYNC: mobile does not update partner
            new_mobile = '+1 202 555 6543'
            new_mobile_formatted = phone_format(new_mobile, 'US', '1', force_format="INTERNATIONAL")
            lead_form.mobile = new_mobile
            lead_form.save()
            self.assertEqual(lead.mobile, new_mobile_formatted)
            self.assertEqual(partner.mobile, partner_mobile)

            # LEAD/PARTNER SYNC: reseting lead values also resets partner for email
            # and phone, but not for mobile
            lead_form.email_from, lead_form.phone, lead.mobile = False, False, False
            self.assertTrue(lead_form.partner_email_update)
            self.assertTrue(lead_form.partner_phone_update)
            lead_form.save()
            self.assertFalse(partner.email)
            self.assertFalse(partner.email_normalized)
            self.assertFalse(partner.phone)
            self.assertFalse(lead.phone)
            self.assertFalse(lead.mobile)
            self.assertFalse(lead.phone_sanitized)
            self.assertEqual(partner.mobile, partner_mobile)
            # if SMS is uninstalled, phone_sanitized is not available on partner
            if 'phone_sanitized' in partner:
                self.assertEqual(partner.phone_sanitized, partner_mobile_sanitized,
                                'Partner sanitized should be computed on mobile')

    @users('user_sales_manager')
    def test_crm_lead_partner_sync_email_phone_corner_cases(self):
        """ Test corner cases of email and phone sync (False versus '', formatting
        differences, wrong input, ...) """
        test_email = 'amy.wong@test.example.com'
        lead = self.lead_1.with_user(self.env.user)
        lead.write({'phone': False})  # reset phone to start with all Falsy values
        contact = self.env['res.partner'].create({
            'name': 'NoContact Partner',
            'phone': '',
            'email': '',
            'mobile': '',
        })

        # This is a type == 'lead', not a type == 'opportunity'
        # {'invisible': ['|', ('type', '=', 'opportunity'), ('is_partner_visible', '=', False)]}
        # lead.is_partner_visible = bool(lead.type == 'opportunity' or lead.partner_id or is_debug_mode)
        # Hence, debug mode required for `partner_id` to be visible
        with self.debug_mode():
            lead_form = Form(lead)
            self.assertEqual(lead_form.email_from, test_email)
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)

            # email: False versus empty string
            lead_form.partner_id = contact
            self.assertTrue(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.email_from = ''
            self.assertFalse(lead_form.partner_email_update)
            lead_form.email_from = False
            self.assertFalse(lead_form.partner_email_update)

            # phone: False versus empty string
            lead_form.phone = '+1 202-555-0888'
            self.assertFalse(lead_form.partner_email_update)
            self.assertTrue(lead_form.partner_phone_update)
            lead_form.phone = ''
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.phone = False
            self.assertFalse(lead_form.partner_phone_update)

            # email/phone: formatting should not trigger ribbon
            lead.write({
                'email_from': '"My Name" <%s>' % test_email,
                'phone': '+1 202-555-0888',
            })
            contact.write({
                'email': '"My Name" <%s>' % test_email,
                'phone': '+1 202-555-0888',
            })

            lead_form = Form(lead)
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.partner_id = contact
            self.assertFalse(lead_form.partner_email_update)
            self.assertFalse(lead_form.partner_phone_update)
            lead_form.email_from = '"Another Name" <%s>' % test_email  # same email normalized
            self.assertFalse(lead_form.partner_email_update, 'Formatting-only change should not trigger write')
            self.assertFalse(lead_form.partner_phone_update, 'Formatting-only change should not trigger write')
            lead_form.phone = '2025550888'  # same number but another format
            self.assertFalse(lead_form.partner_email_update, 'Formatting-only change should not trigger write')
            self.assertFalse(lead_form.partner_phone_update, 'Formatting-only change should not trigger write')

            # wrong value are also propagated
            lead_form.phone = '666 789456789456789456'
            self.assertTrue(lead_form.partner_phone_update)

            # test country propagation allowing to correctly compute sanitized numbers
            # by adding missing relevant information from contact
            be_country = self.env.ref('base.be')
            contact.write({
                'country_id': be_country.id,
                'phone': '+32456001122',
            })
            lead.write({'country_id': False})
            lead_form = Form(lead)
            lead_form.partner_id = contact
            lead_form.phone = '0456 00 11 22'
            self.assertFalse(lead_form.partner_phone_update)
            self.assertEqual(lead_form.country_id, be_country)


    @users('user_sales_manager')
    def test_crm_lead_stages(self):
        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.team_id, self.sales_team_1)

        lead.convert_opportunity(self.contact_1)
        self.assertEqual(lead.team_id, self.sales_team_1)

        lead.action_set_won()
        self.assertEqual(lead.probability, 100.0)
        self.assertEqual(lead.stage_id, self.stage_gen_won)  # generic won stage has lower sequence than team won stage

    @users('user_sales_manager')
    def test_crm_lead_unlink_calendar_event(self):
        """ Test res_id / res_model is reset (and hide document button in calendar
        event form view) when lead is unlinked """
        lead = self.env['crm.lead'].create({'name': 'Lead With Meetings'})
        meetings = self.env['calendar.event'].create([
            {
                'name': 'Meeting 1 of Lead',
                'res_id': lead.id,
                'res_model_id': self.env['ir.model']._get_id(lead._name),
                'start': '2022-07-12 08:00:00',
                'stop': '2022-07-12 10:00:00',
            }, {
                'name': 'Meeting 2 of Lead',
                'opportunity_id': lead.id,
                'res_id': lead.id,
                'res_model_id': self.env['ir.model']._get_id(lead._name),
                'start': '2022-07-13 08:00:00',
                'stop': '2022-07-13 10:00:00',
            }
        ])
        self.assertEqual(len(lead.calendar_event_ids), 1)
        self.assertEqual(meetings.opportunity_id, lead)
        self.assertEqual(meetings.mapped('res_id'), [lead.id, lead.id])
        self.assertEqual(meetings.mapped('res_model'), ['crm.lead', 'crm.lead'])
        lead.unlink()
        self.assertEqual(meetings.exists(), meetings)
        self.assertFalse(meetings.opportunity_id)
        self.assertEqual(set(meetings.mapped('res_id')), set([0]))
        self.assertEqual(set(meetings.mapped('res_model')), set([False]))

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

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_mailgateway(self):
        new_lead = self.format_and_process(
            INCOMING_EMAIL,
            'unknown.sender@test.example.com',
            self.sales_team_1.alias_email,
            subject='Delivery cost inquiry',
            target_model='crm.lead',
        )
        self.assertEqual(new_lead.email_from, 'unknown.sender@test.example.com')
        self.assertFalse(new_lead.partner_id)
        self.assertEqual(new_lead.name, 'Delivery cost inquiry')

        message = new_lead.with_user(self.user_sales_manager).message_post(
            body='Here is my offer!',
            subtype_xmlid='mail.mt_comment')
        self.assertEqual(message.author_id, self.user_sales_manager.partner_id)

        new_lead._handle_partner_assignment(create_missing=True)
        self.assertEqual(new_lead.partner_id.email, 'unknown.sender@test.example.com')
        self.assertEqual(new_lead.partner_id.team_id, self.sales_team_1)

    @users('user_sales_manager')
    def test_phone_mobile_search(self):
        lead_1 = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'country_id': self.env.ref('base.be').id,
            'phone': '+32485001122',
        })
        lead_2 = self.env['crm.lead'].create({
            'name': 'Lead 2',
            'country_id': self.env.ref('base.be').id,
            'phone': '0032485001122',
        })
        lead_3 = self.env['crm.lead'].create({
            'name': 'Lead 3',
            'country_id': self.env.ref('base.be').id,
            'phone': 'hello',
        })
        lead_4 = self.env['crm.lead'].create({
            'name': 'Lead 3',
            'country_id': self.env.ref('base.be').id,
            'phone': '+32485112233',
        })

        # search term containing less than 3 characters should throw an error (some currently not working)
        with self.assertRaises(UserError):
            self.env['crm.lead'].search([('phone_mobile_search', 'like', '')])
        # with self.assertRaises(UserError):
        #     self.env['crm.lead'].search([('phone_mobile_search', 'like', '7   ')])
        with self.assertRaises(UserError):
            self.env['crm.lead'].search([('phone_mobile_search', 'like', 'c')])
        with self.assertRaises(UserError):
            self.env['crm.lead'].search([('phone_mobile_search', 'like', '+')])
        with self.assertRaises(UserError):
            self.env['crm.lead'].search([('phone_mobile_search', 'like', '5')])
        with self.assertRaises(UserError):
            self.env['crm.lead'].search([('phone_mobile_search', 'like', '42')])

        # + / 00 prefixes do not block search
        self.assertEqual(lead_1 + lead_2, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '+32485001122')
        ]))
        self.assertEqual(lead_1 + lead_2, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '0032485001122')
        ]))
        self.assertEqual(lead_1 + lead_2, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '485001122')
        ]))
        self.assertEqual(lead_1 + lead_2 + lead_4, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '1122')
        ]))

        # textual input still possible
        self.assertEqual(
            self.env['crm.lead'].search([('phone_mobile_search', 'like', 'hello')]),
            lead_3,
            'Should behave like a text field'
        )
        self.assertFalse(
            self.env['crm.lead'].search([('phone_mobile_search', 'like', 'Hello')]),
            'Should behave like a text field (case sensitive)'
        )
        self.assertEqual(
            self.env['crm.lead'].search([('phone_mobile_search', 'ilike', 'Hello')]),
            lead_3,
            'Should behave like a text field (case insensitive)'
        )
        self.assertEqual(
            self.env['crm.lead'].search([('phone_mobile_search', 'like', 'hello123')]),
            self.env['crm.lead'],
            'Should behave like a text field'
        )

    @users('user_sales_manager')
    def test_phone_mobile_search_format(self):
        numbers = [
            # standard
            '0499223311',
            # separators
            '0499/223311', '0499/22.33.11', '0499/22 33 11', '0499/223 311',
            # international format -> currently not working
            # '+32499223311', '0032499223311',
        ]
        leads = self.env['crm.lead'].create([
            {'name': 'Lead %s' % index,
             'country_id': self.env.ref('base.be').id,
             'phone': number,
            }
            for index, number in enumerate(numbers)
        ])

        self.assertEqual(leads, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '0499223311')
        ]))
        self.assertEqual(leads, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '0499/223311')
        ]))
        self.assertEqual(leads, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '0499/22.33.11')
        ]))
        self.assertEqual(leads, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '0499/22 33 11')
        ]))
        self.assertEqual(leads, self.env['crm.lead'].search([
            ('phone_mobile_search', 'like', '0499/223 311')
        ]))

    @users('user_sales_manager')
    def test_phone_mobile_update(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'country_id': self.env.ref('base.us').id,
            'phone': self.test_phone_data[0],
        })
        self.assertEqual(lead.phone, self.test_phone_data[0])
        self.assertFalse(lead.mobile)
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[0])

        lead.write({'phone': False, 'mobile': self.test_phone_data[1]})
        self.assertFalse(lead.phone)
        self.assertEqual(lead.mobile, self.test_phone_data[1])
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[1])

        lead.write({'phone': self.test_phone_data[1], 'mobile': self.test_phone_data[2]})
        self.assertEqual(lead.phone, self.test_phone_data[1])
        self.assertEqual(lead.mobile, self.test_phone_data[2])
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[2])

        # updating country should trigger sanitize computation
        lead.write({'country_id': self.env.ref('base.be').id})
        self.assertEqual(lead.phone, self.test_phone_data[1])
        self.assertEqual(lead.mobile, self.test_phone_data[2])
        self.assertFalse(lead.phone_sanitized)


@tagged('lead_internals')
class TestLeadFormTools(FormatAddressCase):

    def test_address_view(self):
        self.env.company.country_id = self.env.ref('base.us')
        self.assertAddressView('crm.lead')


@tagged('lead_internals')
class TestCrmLeadMailTrackingDuration(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('crm.lead')

    def test_crm_lead_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_crm_lead_mail_tracking_duration_batch(self):
        self._test_record_duration_tracking_batch()

    def test_crm_lead_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()
