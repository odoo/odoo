# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests import common as crm_common
from odoo.fields import Datetime
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadConvert(crm_common.TestLeadConvertCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvert, cls).setUpClass()
        date = Datetime.from_string('2020-01-20 16:00:00')
        cls.crm_lead_dt_mock.now.return_value = date

    @users('user_sales_manager')
    def test_lead_convert_base(self):
        """ Test base method ``convert_opportunity`` or crm.lead model """
        lead = self.lead_1.with_user(self.env.user)
        lead.write({
            'phone': '123456789',
        })
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)
        self.assertEqual(lead.email_from, 'amy.wong@test.example.com')
        lead.convert_opportunity(self.contact_2.id)

        self.assertEqual(lead.type, 'opportunity')
        self.assertEqual(lead.partner_id, self.contact_2)
        self.assertEqual(lead.email_from, self.contact_2.email)
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
        lead.convert_opportunity(self.contact_2.id)

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

        lead.convert_opportunity(self.contact_2.id)
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
    def test_lead_convert_internals(self):
        """ Test internals of convert wizard """
        # ensure initial data to avoid spaghetti test update afterwards
        self.assertFalse(self.lead_1.date_conversion)
        self.assertEqual(self.lead_1.date_open, Datetime.from_string('2020-01-15 11:30:00'))
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_1.team_id, self.sales_team_1)
        self.assertEqual(self.lead_1.stage_id, self.stage_team1_1)

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})

        # test internals of convert wizard
        # self.assertEqual(convert.lead_id, self.lead_1)
        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, 'convert')
        self.assertEqual(convert.action, 'create')

        convert.write({'user_id': self.user_sales_salesman.id})
        convert._onchange_user()
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
        self.assertEqual(new_partner.name, 'Amy Wong')
        self.assertEqual(new_partner.email, 'amy.wong@test.example.com')

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
    def test_lead_merge(self):
        """ Test convert wizard working in merge mode """
        date = Datetime.from_string('2020-01-20 16:00:00')
        self.crm_lead_dt_mock.now.return_value = date

        leads = self._create_duplicates(self.lead_1)

        convert = self.env['crm.lead2opportunity.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id,
            'active_ids': self.lead_1.ids,
        }).create({})

        # test internals of convert wizard
        self.assertEqual(convert.opportunity_ids, self.lead_1 | leads)
        self.assertEqual(convert.user_id, self.lead_1.user_id)
        self.assertEqual(convert.team_id, self.lead_1.team_id)
        self.assertFalse(convert.partner_id)
        self.assertEqual(convert.name, 'merge')
        self.assertEqual(convert.action, 'create')

        convert.write({'user_id': self.user_sales_salesman.id})
        convert._onchange_user()
        self.assertEqual(convert.user_id, self.user_sales_salesman)
        self.assertEqual(convert.team_id, self.sales_team_convert)

        convert.action_apply()
        self.assertEqual(self.lead_1.type, 'opportunity')


@tagged('lead_manage')
class TestLeadConvertBatch(crm_common.TestLeadConvertMassCommon):

    @users('user_sales_manager')
    def test_lead_convert_batch_internals(self):
        """ Test internals of convert wizard, working in batch mode """
        date = Datetime.from_string('2020-01-20 16:00:00')
        self.crm_lead_dt_mock.now.return_value = date

        lead_w_partner = self.lead_w_partner
        self.assertEqual(lead_w_partner.user_id, self.user_sales_manager)
        self.assertEqual(lead_w_partner.team_id, self.sales_team_1)
        self.assertEqual(lead_w_partner.stage_id, self.env['crm.stage'])
        lead_w_contact = self.lead_w_contact
        self.assertEqual(lead_w_contact.user_id, self.user_sales_salesman)
        self.assertEqual(lead_w_contact.team_id, self.sales_team_convert)
        self.assertEqual(lead_w_contact.stage_id, self.stage_gen_1)
        lead_w_email_lost = self.lead_w_email_lost
        self.assertEqual(lead_w_email_lost.user_id, self.user_sales_leads)
        self.assertEqual(lead_w_email_lost.team_id, self.sales_team_1)
        self.assertEqual(lead_w_email_lost.stage_id, self.stage_team1_2)
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


@tagged('lead_manage')
class TestLeadConvertMass(crm_common.TestLeadConvertMassCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertMass, cls).setUpClass()

        cls.leads = cls.lead_1 + cls.lead_w_partner + cls.lead_w_email_lost
        # reset some assigned users to test salesmen assign
        (cls.lead_w_partner | cls.lead_w_email_lost).write({
            'user_id': False
        })

        cls.assign_users = cls.user_sales_manager + cls.user_sales_leads_convert + cls.user_sales_salesman

    @users('user_sales_manager')
    def test_mass_convert_internals(self):
        """ Test internals mass converted in convert mode, without duplicate management """
        leads = self.leads

        mass_convert = self.env['crm.lead2opportunity.partner.mass'].with_context({
            'active_model': 'crm.lead',
            'active_ids': leads.ids,
            'active_id': leads.ids[0]
        }).create({
            'deduplicate': False,
            'user_id': self.user_sales_salesman.id,
            'force_assignation': False,
        })
        mass_convert.onchange_action()
        mass_convert._onchange_user()

        # default values
        self.assertEqual(mass_convert.name, 'convert')
        self.assertEqual(mass_convert.action, 'each_exist_or_create')
        # depending on options
        self.assertEqual(mass_convert.partner_id, self.env['res.partner'])
        self.assertEqual(mass_convert.deduplicate, False)
        self.assertEqual(mass_convert.user_id, self.user_sales_salesman)
        self.assertEqual(mass_convert.team_id, self.sales_team_convert)

        mass_convert.mass_convert()
        for lead in self.lead_1 | self.lead_w_partner:
            self.assertEqual(lead.type, 'opportunity')
            if lead == self.lead_w_partner:
                self.assertEqual(lead.user_id, self.env['res.users'])  # user_id is bypassed
                self.assertEqual(lead.partner_id, self.contact_1)
            elif lead == self.lead_1:
                self.assertEqual(lead.user_id, self.user_sales_leads)  # existing value not forced
                new_partner = lead.partner_id
                self.assertEqual(new_partner.name, 'Amy Wong')
                self.assertEqual(new_partner.email, 'amy.wong@test.example.com')

        # test unforced assignation
        mass_convert.write({
            'user_ids': self.user_sales_salesman.ids,
        })
        mass_convert.mass_convert()
        self.assertEqual(self.lead_w_partner.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)  # existing value not forced

        # lost leads are untouched
        self.assertEqual(self.lead_w_email_lost.type, 'lead')
        self.assertFalse(self.lead_w_email_lost.active)
        self.assertFalse(self.lead_w_email_lost.date_conversion)
        # TDE FIXME: partner creation is done even on lost leads because not checked in wizard
        # self.assertEqual(self.lead_w_email_lost.partner_id, self.env['res.partner'])

    def test_mass_convert_w_salesmen(self):
        leads = self.leads

        mass_convert = self.env['crm.lead2opportunity.partner.mass'].with_context({
            'active_model': 'crm.lead',
            'active_ids': leads.ids,
            'active_id': leads.ids[0]
        }).create({
            'deduplicate': False,
            'user_ids': self.assign_users.ids,
            'force_assignation': True,
        })

        # TDE FIXME: what happens if we mix people from different sales team ? currently nothing, to check
        mass_convert.mass_convert()

        for idx, lead in enumerate(self.leads - self.lead_w_email_lost):
            self.assertEqual(lead.type, 'opportunity')
            assigned_user = self.assign_users[idx % len(self.assign_users)]
            self.assertEqual(lead.user_id, assigned_user)
