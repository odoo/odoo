# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestLeadConvertMassCommon
from odoo.fields import Datetime
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadMerge(TestLeadConvertMassCommon):
    """ During a mixed merge (involving leads and opps), data should be handled a certain way following their type
    (m2o, m2m, text, ...). """

    @classmethod
    def setUpClass(cls):
        super(TestLeadMerge, cls).setUpClass()

        cls.leads = cls.lead_1 + cls.lead_w_partner + cls.lead_w_contact + cls.lead_w_email + cls.lead_w_partner_company + cls.lead_w_email_lost
        # reset some assigned users to test salesmen assign
        (cls.lead_w_partner | cls.lead_w_email_lost).write({
            'user_id': False,
        })
        cls.lead_w_partner.write({'stage_id': False})

        cls.lead_w_contact.write({'description': 'lead_w_contact'})
        cls.lead_w_email.write({'description': 'lead_w_email'})
        cls.lead_1.write({'description': 'lead_1'})
        cls.lead_w_partner.write({'description': 'lead_w_partner'})

        cls.assign_users = cls.user_sales_manager + cls.user_sales_leads_convert + cls.user_sales_salesman

    def test_initial_data(self):
        """ Ensure initial data to avoid spaghetti test update afterwards """
        self.assertFalse(self.lead_1.date_conversion)
        self.assertEqual(self.lead_1.date_open, Datetime.from_string('2020-01-15 11:30:00'))
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)
        self.assertEqual(self.lead_1.team_id, self.sales_team_1)
        self.assertEqual(self.lead_1.stage_id, self.stage_team1_1)

        self.assertEqual(self.lead_w_partner.stage_id, self.env['crm.stage'])
        self.assertEqual(self.lead_w_partner.user_id, self.env['res.users'])
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
        self.assertEqual(self.lead_w_email_lost.user_id, self.env['res.users'])
        self.assertEqual(self.lead_w_email_lost.team_id, self.sales_team_1)

    @users('user_sales_manager')
    def test_lead_merge_internals(self):
        """ Test internals of merge wizard. In this test leads are ordered as

        lead_w_contact --lead---seq=30
        lead_w_email ----lead---seq=3
        lead_1 ----------lead---seq=1
        lead_w_partner --lead---seq=False
        """
        # ensure initial data
        self.lead_w_partner_company.action_set_won()  # won opps should be excluded

        merge = self.env['crm.merge.opportunity'].with_context({
            'active_model': 'crm.lead',
            'active_ids': self.leads.ids,
            'active_id': False,
        }).create({
            'user_id': self.user_sales_leads_convert.id,
        })
        self.assertEqual(merge.team_id, self.sales_team_convert)

        # TDE FIXME: not sure the browse in default get of wizard intended to exlude lost, as it browse ids
        # and exclude inactive leads, but that's not written anywhere ... intended ??
        self.assertEqual(merge.opportunity_ids, self.leads - self.lead_w_partner_company - self.lead_w_email_lost)
        ordered_merge = self.lead_w_contact + self.lead_w_email + self.lead_1 + self.lead_w_partner
        ordered_merge_description = '\n\n'.join(l.description for l in ordered_merge)

        # merged opportunity: in this test, all input are leads. Confidence is based on stage
        # sequence -> lead_w_contact has a stage sequence of 30
        result = merge.action_merge()
        merge_opportunity = self.env['crm.lead'].browse(result['res_id'])
        self.assertFalse((ordered_merge - merge_opportunity).exists())
        self.assertEqual(merge_opportunity, self.lead_w_contact)
        self.assertEqual(merge_opportunity.type, 'lead')
        self.assertEqual(merge_opportunity.description, ordered_merge_description)
        # merged opportunity has updated salesman / team / stage is ok as generic
        self.assertEqual(merge_opportunity.user_id, self.user_sales_leads_convert)
        self.assertEqual(merge_opportunity.team_id, self.sales_team_convert)
        self.assertEqual(merge_opportunity.stage_id, self.stage_gen_1)

    @users('user_sales_manager')
    def test_lead_merge_mixed(self):
        """ In case of mix, opportunities are on top, and result is an opportunity

        lead_1 -------------------opp----seq=1
        lead_w_partner_company ---opp----seq=1 (ID greater)
        lead_w_contact -----------lead---seq=30
        lead_w_email -------------lead---seq=3
        lead_w_partner -----------lead---seq=False
        """
        # ensure initial data
        (self.lead_w_partner_company | self.lead_1).write({'type': 'opportunity'})
        self.assertEqual(self.lead_w_partner_company.stage_id.sequence, 1)
        self.assertEqual(self.lead_1.stage_id.sequence, 1)

        merge = self.env['crm.merge.opportunity'].with_context({
            'active_model': 'crm.lead',
            'active_ids': self.leads.ids,
            'active_id': False,
        }).create({
            'team_id': self.sales_team_convert.id,
            'user_id': False,
        })
        # TDE FIXME: see aa44700dccdc2618e0b8bc94252789264104047c -> no user, no team -> strange
        merge.write({'team_id': self.sales_team_convert.id})

        # TDE FIXME: not sure the browse in default get of wizard intended to exlude lost, as it browse ids
        # and exclude inactive leads, but that's not written anywhere ... intended ??
        self.assertEqual(merge.opportunity_ids, self.leads - self.lead_w_email_lost)
        ordered_merge = self.lead_w_partner_company + self.lead_w_contact + self.lead_w_email + self.lead_w_partner

        result = merge.action_merge()
        merge_opportunity = self.env['crm.lead'].browse(result['res_id'])
        self.assertFalse((ordered_merge - merge_opportunity).exists())
        self.assertEqual(merge_opportunity, self.lead_1)
        self.assertEqual(merge_opportunity.type, 'opportunity')

        # merged opportunity has same salesman (not updated in wizard)
        self.assertEqual(merge_opportunity.user_id, self.user_sales_leads)
        # TDE FIXME: as same uer_id is enforced, team is updated through onchange and therefore stage
        self.assertEqual(merge_opportunity.team_id, self.sales_team_convert)
        # self.assertEqual(merge_opportunity.team_id, self.sales_team_1)
        # TDE FIXME: BUT team_id is computed after checking stage, based on wizard's team_id
        self.assertEqual(merge_opportunity.stage_id, self.stage_team_convert_1)
