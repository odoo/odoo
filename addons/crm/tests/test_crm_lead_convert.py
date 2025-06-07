# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from odoo.addons.crm.tests import common as crm_common
from odoo.fields import Datetime
from odoo.tests import Form, tagged, users

@tagged('lead_manage')
class TestLeadConvertForm(crm_common.TestLeadConvertCommon):

    @users('user_sales_manager')
    def test_form_action_default(self):
        """ Test Lead._find_matching_partner() """
        lead = self.env['crm.lead'].browse(self.lead_1.ids)
        customer = self.env['res.partner'].create({
            "name": "Amy Wong",
            "email": '"Amy, PhD Student, Wong" Tiny <AMY.WONG@test.example.com>'
        })

        wizard = Form(self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id,
            'active_ids': lead.ids,
        }))

        self.assertEqual(wizard.name, 'convert')
        self.assertEqual(wizard.action, 'exist')
        self.assertEqual(wizard.partner_id, customer)

    @users('user_sales_manager')
    def test_form_name_onchange(self):
        """ Test Lead._find_matching_partner() """
        lead = self.env['crm.lead'].browse(self.lead_1.ids)
        lead_dup = lead.copy({'name': 'Duplicate'})
        customer = self.env['res.partner'].create({
            "name": "Amy Wong",
            "email": '"Amy, PhD Student, Wong" Tiny <AMY.WONG@test.example.com>'
        })

        wizard = Form(self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id,
            'active_ids': lead.ids,
        }))

        self.assertEqual(wizard.name, 'merge')
        self.assertEqual(wizard.action, 'exist')
        self.assertEqual(wizard.partner_id, customer)
        self.assertEqual(wizard.duplicated_lead_ids[:], lead + lead_dup)

        wizard.name = 'convert'
        wizard.action = 'create'
        self.assertEqual(wizard.action, 'create', 'Should keep user input')
        self.assertEqual(wizard.name, 'convert', 'Should keep user input')


@tagged('lead_manage')
class TestLeadConvert(crm_common.TestLeadConvertCommon):
    """
    TODO: created partner (handle assignation) has team of lead
    TODO: create partner has user_id  coming from wizard
    """

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvert, cls).setUpClass()
        date = Datetime.from_string('2020-01-20 16:00:00')
        cls.crm_lead_dt_mock.now.return_value = date

    @users('user_sales_manager')
    def test_duplicates_computation(self):
        """ Test Lead._get_lead_duplicates() and check won / probability usage """
        test_lead = self.env['crm.lead'].browse(self.lead_1.ids)
        customer, dup_leads = self._create_duplicates(test_lead)
        dup_leads += self.env['crm.lead'].create([
            {'name': 'Duplicate lead: same email_from, lost',
             'type': 'lead',
             'email_from': test_lead.email_from,
             'probability': 0, 'active': False,
            },
            {'name': 'Duplicate lead: same email_from, proba 0 but not lost',
             'type': 'lead',
             'email_from': test_lead.email_from,
             'probability': 0, 'active': True,
            },
            {'name': 'Duplicate opp: same email_from, won',
             'type': 'opportunity',
             'email_from': test_lead.email_from,
             'probability': 100, 'stage_id': self.stage_team1_won.id,
            },
            {'name': 'Duplicate opp: same email_from, proba 100 but not won',
             'type': 'opportunity',
             'email_from': test_lead.email_from,
             'probability': 100, 'stage_id': self.stage_team1_2.id,
            }
        ])
        lead_lost = dup_leads.filtered(lambda lead: lead.name == 'Duplicate lead: same email_from, lost')
        _opp_proba100 = dup_leads.filtered(lambda lead: lead.name == 'Duplicate opp: same email_from, proba 100 but not won')
        opp_won = dup_leads.filtered(lambda lead: lead.name == 'Duplicate opp: same email_from, won')
        opp_lost = dup_leads.filtered(lambda lead: lead.name == 'Duplicate: lost opportunity')

        test_lead.write({'partner_id': customer.id})

        # not include_lost = remove archived leads as well as 'won' opportunities
        result = test_lead._get_lead_duplicates(
            partner=test_lead.partner_id,
            email=test_lead.email_from,
            include_lost=False
        )
        self.assertEqual(result, test_lead + dup_leads - (lead_lost + opp_won + opp_lost))

        # include_lost = remove archived opp only
        result = test_lead._get_lead_duplicates(
            partner=test_lead.partner_id,
            email=test_lead.email_from,
            include_lost=True
        )
        self.assertEqual(result, test_lead + dup_leads - (lead_lost))

    def test_initial_data(self):
        """ Ensure initial data to avoid spaghetti test update afterwards """
        self.assertFalse(self.lead_1.date_conversion)
        self.assertEqual(self.lead_1.date_open, Datetime.from_string('2020-01-15 11:30:00'))
        self.assertEqual(self.lead_1.lang_id, self.lang_fr)
        self.assertFalse(self.lead_1.mobile)
        self.assertEqual(self.lead_1.phone, '+1 202 555 9999')
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_1.team_id, self.sales_team_1)
        self.assertEqual(self.lead_1.stage_id, self.stage_team1_1)

    @users('user_sales_manager')
    def test_lead_convert_base(self):
        """ Test base method ``convert_opportunity`` or crm.lead model """
        self.contact_2.phone = False  # force Falsy to compare with mobile
        self.assertFalse(self.contact_2.phone)
        lead = self.lead_1.with_user(self.env.user)
        lead.write({
            'phone': '123456789',
        })
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)
        self.assertEqual(lead.email_from, 'amy.wong@test.example.com')
        self.assertEqual(lead.lang_id, self.lang_fr)
        lead.convert_opportunity(self.contact_2)

        self.assertEqual(lead.type, 'opportunity')
        self.assertEqual(lead.partner_id, self.contact_2)
        self.assertEqual(lead.email_from, self.contact_2.email)
        self.assertEqual(lead.lang_id, self.lang_en)
        self.assertEqual(lead.mobile, self.contact_2.mobile)
        self.assertEqual(lead.phone, '123456789')
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)

    @users('user_sales_manager')
    def test_lead_convert_base_corner_cases(self):
        """ Test base method ``convert_opportunity`` or crm.lead model with corner
        cases: inactive, won, stage update, ... """
        # inactive leads are not converted
        lead = self.lead_1.with_user(self.env.user)
        lead.action_archive()
        self.assertFalse(lead.active)
        lead.convert_opportunity(self.contact_2)

        self.assertEqual(lead.type, 'lead')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        lead.action_unarchive()
        self.assertTrue(lead.active)

        # won leads are not converted
        lead.action_set_won()
        # TDE FIXME: set won does not take into account sales team when fetching a won stage
        # self.assertEqual(lead.stage_id, self.stage_team1_won)
        self.assertEqual(lead.stage_id, self.stage_gen_won)
        self.assertEqual(lead.probability, 100)

        lead.convert_opportunity(self.contact_2)
        self.assertEqual(lead.type, 'lead')
        self.assertEqual(lead.partner_id, self.env['res.partner'])

    @users('user_sales_manager')
    def test_lead_convert_base_w_salesmen(self):
        """ Test base method ``convert_opportunity`` while forcing salesmen, as it
        should also force sales team """
        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.team_id, self.sales_team_1)
        lead.convert_opportunity(False, user_ids=self.user_sales_salesman.ids)
        self.assertEqual(lead.user_id, self.user_sales_salesman)
        self.assertEqual(lead.team_id, self.sales_team_convert)
        # TDE FIXME: convert does not recompute stage based on updated team of assigned user
        # self.assertEqual(lead.stage_id, self.stage_team_convert_1)

    @users('user_sales_manager')
    def test_lead_convert_base_w_team(self):
        """ Test base method ``convert_opportunity`` while forcing team """
        lead = self.lead_1.with_user(self.env.user)
        lead.convert_opportunity(False, team_id=self.sales_team_convert.id)
        self.assertEqual(lead.team_id, self.sales_team_convert)
        self.assertEqual(lead.user_id, self.user_sales_leads)
        # TDE FIXME: convert does not recompute stage based on team
        # self.assertEqual(lead.stage_id, self.stage_team_convert_1)

    @users('user_sales_manager')
    def test_lead_convert_corner_cases_crud(self):
        """ Test Lead._find_matching_partner() """
        # email formatting
        other_lead = self.lead_1.copy()
        other_lead.write({'partner_id': self.contact_1.id})

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'default_lead_id': other_lead.id,
        }).create({})
        self.assertEqual(convert.lead_id, other_lead)
        self.assertEqual(convert.partner_id, self.contact_1)
        self.assertEqual(convert.action, 'exist')

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'default_lead_id': other_lead.id,
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
        }).create({})
        self.assertEqual(convert.lead_id, other_lead)
        self.assertEqual(convert.partner_id, self.contact_1)
        self.assertEqual(convert.action, 'exist')

    @users('user_sales_manager')
    def test_lead_convert_corner_cases_matching(self):
        """ Test Lead._find_matching_partner() """
        # email formatting
        self.lead_1.write({
            'email_from': 'Amy Wong <amy.wong@test.example.com>'
        })
        customer = self.env['res.partner'].create({
            'name': 'Different Name',
            'email': 'Wong AMY <AMY.WONG@test.example.com>'
        })

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})
        # TDE FIXME: should take into account normalized email version, not encoded one
        # self.assertEqual(convert.partner_id, customer)

    @users('user_sales_manager')
    def test_lead_convert_no_lang(self):
        """ Ensure converting a lead with an archived language correctly falls back on the default partner language. """
        inactive_lang = self.env["res.lang"].sudo().create({
            'code': 'en_ZZ',
            'name': 'Inactive Lang',
            'active': False,
        })

        lead = self.lead_1.with_user(self.env.user)
        lead.lang_id = inactive_lang

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({'action': 'create'})
        convert.action_apply()
        self.assertTrue(lead.partner_id)
        self.assertEqual(lead.partner_id.lang, 'en_US')

    @users('user_sales_manager')
    def test_lead_convert_internals(self):
        """ Test internals of convert wizard """
        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})

        # test internals of convert wizard
        self.assertEqual(convert.lead_id, self.lead_1)
        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, 'convert')
        self.assertEqual(convert.action, 'create')

        convert.write({'user_id': self.user_sales_salesman.id})
        self.assertEqual(convert.user_id, self.user_sales_salesman)
        self.assertEqual(convert.team_id, self.sales_team_convert)

        convert.action_apply()
        # convert test
        self.assertEqual(self.lead_1.type, 'opportunity')
        self.assertEqual(self.lead_1.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_1.team_id, self.sales_team_convert)
        # TDE FIXME: stage is linked to the old sales team and is not updated when converting, could be improved
        # self.assertEqual(self.lead_1.stage_id, self.stage_gen_1)
        # partner creation test
        new_partner = self.lead_1.partner_id
        self.assertEqual(new_partner.email, 'amy.wong@test.example.com')
        self.assertEqual(new_partner.lang, self.lang_fr.code)
        self.assertEqual(new_partner.phone, '+1 202 555 9999')
        self.assertEqual(new_partner.name, 'Amy Wong')

    @users('user_sales_manager')
    def test_lead_convert_action_exist(self):
        """ Test specific use case of 'exist' action in conver wizard """
        self.lead_1.write({'partner_id': self.contact_1.id})

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})
        self.assertEqual(convert.action, 'exist')
        convert.action_apply()
        self.assertEqual(self.lead_1.type, 'opportunity')
        self.assertEqual(self.lead_1.partner_id, self.contact_1)

    @users('user_sales_manager')
    def test_lead_convert_action_nothing(self):
        """ Test specific use case of 'nothing' action in conver wizard """
        self.lead_1.write({'contact_name': False})

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})
        self.assertEqual(convert.action, 'nothing')
        convert.action_apply()
        self.assertEqual(self.lead_1.type, 'opportunity')
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_1.team_id, self.sales_team_1)
        self.assertEqual(self.lead_1.stage_id, self.stage_team1_1)
        self.assertEqual(self.lead_1.partner_id, self.env['res.partner'])

    @users('user_sales_manager')
    def test_lead_convert_contact_mutlicompany(self):
        """ Check the wizard convert to opp don't find contact
        You are not able to see because they belong to another company """
        # Use superuser_id because creating a company with a user add directly
        # the company in company_ids of the user.
        company_2 = self.env['res.company'].with_user(SUPERUSER_ID).create({'name': 'Company 2'})
        partner_company_2 = self.env['res.partner'].with_user(SUPERUSER_ID).create({
            'name': 'Contact in other company',
            'email': 'test@company2.com',
            'company_id': company_2.id,
        })
        lead = self.env['crm.lead'].create({
            'name': 'LEAD',
            'type': 'lead',
            'email_from': 'test@company2.com',
        })
        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id,
            'active_ids': lead.ids,
        }).create({'name': 'convert', 'action': 'exist'})
        self.assertNotEqual(convert.partner_id, partner_company_2,
            "Conversion wizard should not be able to find the partner from another company")

    @users('user_sales_manager')
    def test_lead_convert_same_partner(self):
        """ Check that we don't erase lead information
        with existing partner info if the partner is already set
        """
        partner = self.env['res.partner'].create({
            'name': 'Empty partner',
        })
        lead = self.env['crm.lead'].create({
            'name': 'LEAD',
            'partner_id': partner.id,
            'type': 'lead',
            'email_from': 'demo@test.com',
            'lang_id': self.lang_fr.id,
            'street': 'my street',
            'city': 'my city',
        })
        lead.convert_opportunity(partner)
        self.assertEqual(lead.email_from, 'demo@test.com', 'Email From should be preserved during conversion')
        self.assertEqual(lead.lang_id, self.lang_fr, 'Lang should be preserved during conversion')
        self.assertEqual(lead.street, 'my street', 'Street should be preserved during conversion')
        self.assertEqual(lead.city, 'my city', 'City should be preserved during conversion')
        self.assertEqual(partner.lang, 'en_US')

    @users('user_sales_manager')
    def test_lead_convert_properties_preserve(self):
        """Verify that the properties are preserved when converting."""
        initial_team = self.lead_1.with_env(self.env).team_id
        self.lead_1.lead_properties = [{
            'name': 'test',
            'type': 'char',
            'value': 'test value',
            'definition_changed': True,
        }]
        self.lead_1.convert_opportunity(False)
        self.assertEqual(self.lead_1.team_id, initial_team)
        self.assertEqual(self.lead_1.lead_properties, {'test': 'test value'})

        # re-writing the team, but keeping the same value should not reset the properties
        self.lead_1.write({'team_id': self.lead_1.team_id.id})
        self.assertEqual(self.lead_1.lead_properties, {'test': 'test value'})

    @users('user_sales_manager')
    def test_lead_convert_properties_reset(self):
        """Verify that the properties are reset when converting if the team changed."""
        initial_team = self.lead_1.with_env(self.env).team_id
        self.lead_1.lead_properties = [{
            'name': 'test',
            'type': 'char',
            'value': 'test value',
            'definition_changed': True,
        }]
        self.lead_1.convert_opportunity(False, user_ids=self.user_sales_salesman.ids)
        self.assertNotEqual(self.lead_1.team_id, initial_team)
        self.assertFalse(self.lead_1.lead_properties)

    @users('user_sales_manager')
    def test_lead_merge(self):
        """ Test convert wizard working in merge mode """
        date = Datetime.from_string('2020-01-20 16:00:00')
        self.crm_lead_dt_mock.now.return_value = date

        leads = self.env['crm.lead']
        for x in range(2):
            leads |= self.env['crm.lead'].create({
                'name': 'Dup-%02d-%s' % (x+1, self.lead_1.name),
                'type': 'lead', 'user_id': False, 'team_id': self.lead_1.team_id.id,
                'contact_name': 'Duplicate %02d of %s' % (x+1, self.lead_1.contact_name),
                'email_from': self.lead_1.email_from,
                'probability': 10,
            })

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})

        # test internals of convert wizard
        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | leads)
        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, 'merge')
        self.assertEqual(convert.action, 'create')

        convert.write({'user_id': self.user_sales_salesman.id})
        self.assertEqual(convert.user_id, self.user_sales_salesman)
        self.assertEqual(convert.team_id, self.sales_team_convert)

        convert.action_apply()
        self.assertEqual(self.lead_1.type, 'opportunity')

    @users('user_sales_manager')
    def test_lead_merge_last_created(self):
        """
        Test convert wizard is not deleted in merge mode when the original assigned lead is deleted
        """
        date = Datetime.from_string('2020-01-20 16:00:00')
        self.crm_lead_dt_mock.now.return_value = date

        last_lead = self.env['crm.lead'].create({
            'name': f'Duplicate of {self.lead_1.contact_name}',
            'type': 'lead', 'user_id': False, 'team_id': self.lead_1.team_id.id,
            'contact_name': f'Duplicate of {self.lead_1.contact_name}',
            'email_from': self.lead_1.email_from,
            'probability': 10,
        })

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': last_lead.id,
            'active_ids': last_lead.ids,
        }).create({})

        # test main lead on wizard
        self.assertEqual(convert.lead_id, last_lead)
        convert.action_apply()
        self.assertTrue(convert.exists(), 'Wizard cannot be deleted via cascade!')
        self.assertEqual(convert.lead_id, self.lead_1, "Lead must be the result opportunity!")
        self.assertEqual(self.lead_1.type, 'opportunity')
        self.assertFalse(last_lead.exists(), 'The last lead must be merged with the first one!')

    @users('user_sales_salesman')
    def test_lead_merge_user(self):
        """ Test convert wizard working in merge mode with sales user """
        date = Datetime.from_string('2020-01-20 16:00:00')
        self.crm_lead_dt_mock.now.return_value = date

        leads = self.env['crm.lead']
        for x in range(2):
            leads |= self.env['crm.lead'].create({
                'name': 'Dup-%02d-%s' % (x+1, self.lead_1.name),
                'type': 'lead', 'user_id': False, 'team_id': self.lead_1.team_id.id,
                'contact_name': 'Duplicate %02d of %s' % (x+1, self.lead_1.contact_name),
                'email_from': self.lead_1.email_from,
                'probability': 10,
            })

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': leads[0].id,
            'active_ids': leads[0].ids,
        }).create({})

        # test internals of convert wizard
        self.assertEqual(convert.duplicated_lead_ids, leads)
        self.assertEqual(convert.name, 'merge')
        self.assertEqual(convert.action, 'create')

        convert.write({'user_id': self.user_sales_salesman.id})
        self.assertEqual(convert.user_id, self.user_sales_salesman)
        self.assertEqual(convert.team_id, self.sales_team_convert)

        convert.action_apply()
        self.assertEqual(leads[0].type, 'opportunity')

    @users('user_sales_manager')
    def test_lead_merge_duplicates(self):
        """ Test Lead._get_lead_duplicates() and check: partner / email fallbacks """
        customer, dup_leads = self._create_duplicates(self.lead_1)
        lead_partner = dup_leads.filtered(lambda lead: lead.name == 'Duplicate: customer ID')
        self.assertTrue(bool(lead_partner))

        self.lead_1.write({
            'partner_id': customer.id,
        })
        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})
        self.assertEqual(convert.partner_id, customer)
        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | dup_leads)

        # Check: partner fallbacks
        self.lead_1.write({
            'email_from': False,
            'partner_id': customer.id,
        })
        customer.write({'email': False})
        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})
        self.assertEqual(convert.partner_id, customer)
        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | lead_partner)

    @users('user_sales_manager')
    def test_lead_merge_duplicates_flow(self):
        """ Test Lead._get_lead_duplicates() + merge with active_test """

        # Check: email formatting
        self.lead_1.write({
            'email_from': 'Amy Wong <amy.wong@test.example.com>'
        })
        customer, dup_leads = self._create_duplicates(self.lead_1)
        opp_lost = dup_leads.filtered(lambda lead: lead.name == 'Duplicate: lost opportunity')
        self.assertTrue(bool(opp_lost))

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})
        self.assertEqual(convert.partner_id, customer)
        self.assertEqual(convert.duplicated_lead_ids, self.lead_1 | dup_leads)

        convert.action_apply()
        self.assertEqual(
            (self.lead_1 | dup_leads).exists(),
            opp_lost)


@tagged('lead_manage')
class TestLeadConvertBatch(crm_common.TestLeadConvertMassCommon):

    def test_initial_data(self):
        """ Ensure initial data to avoid spaghetti test update afterwards """
        self.assertFalse(self.lead_1.date_conversion)
        self.assertEqual(self.lead_1.date_open, Datetime.from_string('2020-01-15 11:30:00'))
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_1.team_id, self.sales_team_1)
        self.assertEqual(self.lead_1.stage_id, self.stage_team1_1)

        self.assertEqual(self.lead_w_partner.stage_id, self.env['crm.stage'])
        self.assertEqual(self.lead_w_partner.user_id, self.user_sales_manager)
        self.assertEqual(self.lead_w_partner.team_id, self.sales_team_1)

        self.assertEqual(self.lead_w_partner_company.stage_id, self.stage_team1_1)
        self.assertEqual(self.lead_w_partner_company.user_id, self.user_sales_manager)
        self.assertEqual(self.lead_w_partner_company.team_id, self.sales_team_1)

        self.assertEqual(self.lead_w_contact.stage_id, self.stage_gen_1)
        self.assertEqual(self.lead_w_contact.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_w_contact.team_id, self.sales_team_convert)

        self.assertEqual(self.lead_w_email.stage_id, self.stage_gen_1)
        self.assertEqual(self.lead_w_email.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_w_email.team_id, self.sales_team_convert)

        self.assertEqual(self.lead_w_email_lost.stage_id, self.stage_team1_2)
        self.assertEqual(self.lead_w_email_lost.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_w_email_lost.team_id, self.sales_team_1)

    @users('user_sales_manager')
    def test_lead_convert_batch_internals(self):
        """ Test internals of convert wizard, working in batch mode """
        date = self.env.cr.now()

        lead_w_partner = self.lead_w_partner
        lead_w_contact = self.lead_w_contact
        lead_w_email_lost = self.lead_w_email_lost
        lead_w_email_lost.action_set_lost()
        self.assertEqual(lead_w_email_lost.active, False)

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': (self.lead_1 | lead_w_partner | lead_w_contact | lead_w_email_lost).ids,
        }).create({})

        # test internals of convert wizard
        # self.assertEqual(convert.lead_id, self.lead_1)
        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, 'convert')
        self.assertEqual(convert.action, 'create')

        convert.action_apply()
        self.assertEqual(convert.user_id, self.user_sales_leads)
        self.assertEqual(convert.team_id, self.sales_team_1)
        # lost leads are not converted (see crm_lead.convert_opportunity())
        self.assertFalse(lead_w_email_lost.active)
        self.assertFalse(lead_w_email_lost.date_conversion)
        self.assertEqual(lead_w_email_lost.partner_id, self.env['res.partner'])
        self.assertEqual(lead_w_email_lost.stage_id, self.stage_team1_2)  # did not change
        # other leads are converted into opportunities
        for opp in (self.lead_1 | lead_w_partner | lead_w_contact):
            # team management update: opportunity linked to chosen wizard values
            self.assertEqual(opp.type, 'opportunity')
            self.assertTrue(opp.active)
            self.assertEqual(opp.user_id, convert.user_id)
            self.assertEqual(opp.team_id, convert.team_id)
            # dates update: convert set them to now
            self.assertEqual(opp.date_open, date)
            self.assertEqual(opp.date_conversion, date)
            # stage update (depends on previous value)
            if opp == self.lead_1:
                self.assertEqual(opp.stage_id, self.stage_team1_1)  # did not change
            elif opp == lead_w_partner:
                self.assertEqual(opp.stage_id, self.stage_team1_1)  # is set to default stage of sales_team_1
            elif opp == lead_w_contact:
                self.assertEqual(opp.stage_id, self.stage_gen_1)  # did not change
            else:
                self.assertFalse(True)
