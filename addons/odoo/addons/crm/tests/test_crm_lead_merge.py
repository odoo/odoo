# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timedelta

from odoo.addons.crm.tests.common import TestLeadConvertMassCommon
from odoo.fields import Datetime
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


class TestLeadMergeCommon(TestLeadConvertMassCommon):
    """ During a mixed merge (involving leads and opps), data should be handled a certain way following their type
    (m2o, m2m, text, ...). """

    @classmethod
    def setUpClass(cls):
        super(TestLeadMergeCommon, cls).setUpClass()

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


@tagged('lead_manage')
class TestLeadMerge(TestLeadMergeCommon):

    def _run_merge_wizard(self, leads):
        res = self.env['crm.merge.opportunity'].with_context({
            'active_model': 'crm.lead',
            'active_ids': leads.ids,
            'active_id': False,
        }).create({
            'team_id': False,
            'user_id': False,
        }).action_merge()
        return self.env['crm.lead'].browse(res['res_id'])

    def test_initial_data(self):
        """ Ensure initial data to avoid spaghetti test update afterwards

        Original order:

        lead_w_contact ----------lead---seq=3----proba=15
        lead_w_email ------------lead---seq=3----proba=15
        lead_1 ------------------lead---seq=1----proba=?
        lead_w_partner ----------lead---seq=False---proba=10
        lead_w_partner_company --lead---seq=False---proba=15
        """
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
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_address_not_propagated(self):
        """All addresses have the same number of non-empty address fields, take the first one (lead_w_contact)
        because it's the lead that has the best confidence level after being sorted with '_sort_by_confidence_level'"""
        initial_address = {
            'street': 'Test street',
            'street2': 'Test street2',
            'city': 'Test City',
            'zip': '5000',
            'state_id': False,
            'country_id': self.env.ref('base.be'),
        }
        self.lead_w_contact.write(initial_address)

        (self.leads - self.lead_w_contact).write({
            'street': 'Other street',
            'street2': 'Other street2',
            'city': 'Other City',
            'zip': '6666',
            'state_id': self.env.ref('base.state_us_1'),
            'country_id': False,
        })

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)
        with self.assertLeadMerged(self.lead_w_contact, leads, **initial_address):
            leads._merge_opportunity(auto_unlink=False, max_length=None)

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_address_propagated(self):
        """Test that the address with the most non-empty fields is propagated.

        Should take the address of "lead_w_partner" (maximum number of non-empty address
        fields and with an highest rank than "lead_w_email_lost")
        """
        self.leads.write({
            'street': 'Original street',
            'street2': False,
            'city': False,
            'zip': False,
            'state_id': False,
            'country_id': False,
        })
        new_address = {
            'street': 'New street',
            'street2': False,
            'city': 'New City',
            'zip': False,
            'state_id': False,
            'country_id': False,
        }
        self.lead_w_partner.write(new_address)
        self.lead_w_email_lost.write({
            'street': 'Other street',
            'street2': False,
            'city': 'Other City',
            'zip': False,
            'state_id': False,
            'country_id': False,
        })

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)

        with self.assertLeadMerged(self.lead_w_contact, leads, **new_address):
            leads._merge_opportunity(auto_unlink=False, max_length=None)

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_internals(self):
        """ Test internals of merge wizard. In this test leads are ordered as

        lead_w_contact --lead---seq=3---probability=25
        lead_w_email ----lead---seq=3---probability=15
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
        ordered_merge_description = '<br><br>'.join(l.description for l in ordered_merge)

        # merged opportunity: in this test, all input are leads. Confidence is based on stage
        # sequence -> lead_w_contact has a stage sequence of 3 and probability is greater
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
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_mixed(self):
        """ In case of mix, opportunities are on top, and result is an opportunity

        lead_1 -------------------opp----seq=1---probability=60
        lead_w_partner_company ---opp----seq=1---probability=50
        lead_w_contact -----------lead---seq=3---probability=25
        lead_w_email -------------lead---seq=3---probability=15
        lead_w_partner -----------lead---seq=False
        """
        # ensure initial data
        (self.lead_w_partner_company | self.lead_1).write({'type': 'opportunity'})
        self.lead_1.write({'probability': 60})

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

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_probability_auto(self):
        """ Check master lead keeps its automated probability when merged. """
        self.lead_1.write({'type': 'opportunity', 'probability': self.lead_1.automated_probability})
        self.assertTrue(self.lead_1.is_automated_probability)
        leads = self.env['crm.lead'].browse((self.lead_1 + self.lead_w_partner + self.lead_w_partner_company).ids)
        merged_lead = self._run_merge_wizard(leads)
        self.assertEqual(merged_lead, self.lead_1)
        self.assertTrue(merged_lead.is_automated_probability, "lead with Auto proba should remain with auto probability")

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_probability_auto_empty(self):
        """ Check master lead keeps its automated probability when merged
        even if its probability is 0. """
        self.lead_1.write({'type': 'opportunity', 'probability': 0, 'automated_probability': 0})
        self.assertTrue(self.lead_1.is_automated_probability)
        leads = self.env['crm.lead'].browse((self.lead_1 + self.lead_w_partner + self.lead_w_partner_company).ids)
        merged_lead = self._run_merge_wizard(leads)
        self.assertEqual(merged_lead, self.lead_1)
        self.assertTrue(merged_lead.is_automated_probability, "lead with Auto proba should remain with auto probability")

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_probability_manual(self):
        """ Check master lead keeps its manual probability when merged. """
        self.lead_1.write({'probability': 60})
        self.assertFalse(self.lead_1.is_automated_probability)
        leads = self.env['crm.lead'].browse((self.lead_1 + self.lead_w_partner + self.lead_w_partner_company).ids)
        merged_lead = self._run_merge_wizard(leads)
        self.assertEqual(merged_lead, self.lead_1)
        self.assertEqual(merged_lead.probability, 60, "Manual Probability should remain the same after the merge")
        self.assertFalse(merged_lead.is_automated_probability)

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_lead_merge_probability_manual_empty(self):
        """ Check master lead keeps its manual probability when merged even if
        its probability is 0. """
        self.lead_1.write({'type': 'opportunity', 'probability': 0})
        leads = self.env['crm.lead'].browse((self.lead_1 + self.lead_w_partner + self.lead_w_partner_company).ids)
        merged_lead = self._run_merge_wizard(leads)
        self.assertEqual(merged_lead, self.lead_1)
        self.assertEqual(merged_lead.probability, 0, "Manual Probability should remain the same after the merge")
        self.assertFalse(merged_lead.is_automated_probability)

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_merge_method(self):
        """ In case of mix, opportunities are on top, and result is an opportunity

        lead_1 -------------------opp----seq=1---probability=50
        lead_w_partner_company ---opp----seq=1---probability=50 (ID greater)
        lead_w_contact -----------lead---seq=3
        lead_w_email -------------lead---seq=3
        lead_w_partner -----------lead---seq=False
        """
        # ensure initial data
        (self.lead_w_partner_company | self.lead_1).write({'type': 'opportunity', 'probability': 50})
        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)

        # lead_w_partner is lost, check that the "lost_reason" is not propagated
        # because "lead_1" is not lost
        lost_reason = self.env['crm.lost.reason'].create({'name': 'Test Reason'})
        self.lead_w_partner.write({
            'lost_reason_id': lost_reason,
            'probability': 0,
        })

        all_tags = self.leads.mapped('tag_ids')

        with self.assertLeadMerged(self.lead_1, leads,
                                   name='Nibbler Spacecraft Request',
                                   partner_id=self.contact_company_1,
                                   priority='2',
                                   lost_reason_id=False,
                                   tag_ids=all_tags):
            leads._merge_opportunity(auto_unlink=False, max_length=None)

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_merge_method_propagate_lost_reason(self):
        """Check that the lost reason is propagated to the final lead if it's lost."""
        self.leads.write({
            'probability': 0,
            'automated_probability': 50,  # Do not automatically update the probability
        })

        lost_reason = self.env['crm.lost.reason'].create({'name': 'Test Reason'})
        self.lead_w_partner.lost_reason_id = lost_reason

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)

        with self.assertLeadMerged(leads[0], leads, lost_reason_id=lost_reason):
            leads._merge_opportunity(auto_unlink=False, max_length=None)

    @users('user_sales_manager')
    def test_lead_merge_properties_formatting(self):
        lead = self.lead_1
        partners = self.env['res.partner'].create([{'name': 'Alice'}, {'name': 'Bob'}])

        lead.lead_properties = [{
            'type': 'many2one',
            'comodel': 'res.partner',
            'name': 'test_many2one',
            'string': 'My Partner',
            'value': partners[0].id,
            'definition_changed': True,
        }, {
            'type': 'many2many',
            'comodel': 'res.partner',
            'name': 'test_many2many',
            'string': 'My Partners',
            'value': partners.ids,
        }, {
            'type': 'selection',
            'selection': [['a', 'A'], ['b', 'B']],
            'name': 'test_selection',
            'string': 'My Selection',
            'value': 'a',
        }, {
            'type': 'tags',
            'tags': [['a', 'A', 1], ['b', 'B', 2], ['c', 'C', 3]],
            'name': 'test_tags',
            'string': 'My Tags',
            'value': ['a', 'c'],
        }, {
            'type': 'boolean',
            'name': 'test_boolean',
            'string': 'My Boolean',
            'value': True,
        }, {
            'type': 'integer',
            'name': 'test_integer',
            'string': 'My Integer',
            'value': 1337,
        }, {
            'type': 'datetime',
            'name': 'test_datetime',
            'string': 'My Datetime',
            'value': '2022-02-21 16:11:42',
        }]

        expected = [{
            'label': 'My Partner',
            'value': 'Alice',
        }, {
            'label': 'My Partners',
            'values': [
                {'name': 'Alice'},
                {'name': 'Bob'},
            ],
        }, {
            'label': 'My Selection',
            'value': 'A',
        }, {
            'label': 'My Tags',
            'values': [
                {'name': 'A', 'color': 1},
                {'name': 'C', 'color': 3},
            ],
        }, {
            'label': 'My Boolean',
            'value': 'Yes',
        }, {
            'label': 'My Integer',
            'value': 1337,
        }, {
            'label': 'My Datetime',
            # datetime are stored as string because they are not JSONifiable
            'value': '2022-02-21 16:11:42',
        }]

        self.assertEqual(expected, lead._format_properties())

        # check the rendered template
        result = self.env['ir.qweb']._render(
            'crm.crm_lead_merge_summary',
            {'opportunities': lead, 'is_html_empty': lambda x: True})
        self.assertIn("o_tag_color_1", result)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)

    @users('user_sales_manager')
    def test_merge_method_dependencies(self):
        """ Test if dependences for leads are not lost while merging leads. In
        this test leads are ordered as

        lead_w_partner_company ---opp----seq=1 (ID greater)
        lead_w_contact -----------lead---seq=3
        lead_w_email -------------lead---seq=3----------------attachments
        lead_1 -------------------lead---seq=1----------------activity+meeting
        lead_w_partner -----------lead---seq=False
        """
        self.env['crm.lead'].browse(self.lead_w_partner_company.ids).write({'type': 'opportunity'})

        # create side documents
        attachments = self.env['ir.attachment'].create([
            {'name': '%02d.txt' % idx,
             'datas': base64.b64encode(b'Att%02d' % idx),
             'res_model': 'crm.lead',
             'res_id': self.lead_w_email.id,
            } for idx in range(4)
        ])
        lead_1 = self.env['crm.lead'].browse(self.lead_1.ids)
        activity = lead_1.activity_schedule('crm.lead_test_activity_1')
        calendar_event = self.env['calendar.event'].create({
            'name': 'Meeting with partner',
            'activity_ids': [(4, activity.id)],
            'start': '2021-06-12 21:00:00',
            'stop': '2021-06-13 00:00:00',
            'res_model_id': self.env['ir.model']._get('crm.crm_lead').id,
            'res_id': lead_1.id,
            'opportunity_id': lead_1.id,
        })

        # run merge and check documents are moved to the master record
        merge = self.env['crm.merge.opportunity'].with_context({
            'active_model': 'crm.lead',
            'active_ids': self.leads.ids,
            'active_id': False,
        }).create({
            'team_id': self.sales_team_convert.id,
            'user_id': False,
        })
        result = merge.action_merge()
        master_lead = self.leads.filtered(lambda lead: lead.id == result['res_id'])

        # check result of merge process
        self.assertEqual(master_lead, self.lead_w_partner_company)
        # records updated
        self.assertEqual(calendar_event.opportunity_id, master_lead)
        self.assertEqual(calendar_event.res_id, master_lead.id)
        self.assertTrue(all(att.res_id == master_lead.id for att in attachments))
        # 2many accessors updated
        self.assertEqual(master_lead.activity_ids, activity)
        self.assertEqual(master_lead.calendar_event_ids, calendar_event)

    @users('user_sales_manager')
    @mute_logger('odoo.models.unlink')
    def test_merge_method_followers(self):
        """ Test that the followers of the leads are added in the destination lead.

        They should be added if:
        - The related partner was active on the lead (posted a message in the last 30 days)
        - The related partner is not already following the destination lead

        Leads                       Followers           Info
        ---------------------------------------------------------------------------------
        lead_w_contact              contact_1           OK (destination lead)
        lead_w_email                contact_1           KO (already following the destination lead)
                                    contact_2           OK (active on lead_w_email)
                                    contact_company     KO (most recent message on lead_w_email is 35 days ago, message
                                                            on lead_w_partner is not counted as they don't follow it)
        lead_w_partner              contact_2           KO (already added with lead_w_email)
        lead_w_partner_company
        """
        self.leads.message_follower_ids.unlink()
        self.leads.message_ids.unlink()

        self.lead_w_contact.message_subscribe([self.contact_1.id])
        self.lead_w_email.message_subscribe([self.contact_1.id, self.contact_2.id, self.contact_company.id])
        self.lead_w_partner.message_subscribe([self.contact_2.id])

        self.env['mail.message'].create([{
            'author_id': self.contact_1.id,
            'model': 'crm.lead',
            'res_id': self.lead_w_contact.id,
            'date': Datetime.now() - timedelta(days=1),
            'subtype_id': self.ref('mail.mt_comment'),
            'reply_to': False,
            'body': 'Test follower',
        }, {
            'author_id': self.contact_1.id,
            'model': 'crm.lead',
            'res_id': self.lead_w_email.id,
            'date': Datetime.now() - timedelta(days=20),
            'subtype_id': self.ref('mail.mt_comment'),
            'reply_to': False,
            'body': 'Test follower',
        }, {
            'author_id': self.contact_2.id,
            'model': 'crm.lead',
            'res_id': self.lead_w_email.id,
            'date': Datetime.now() - timedelta(days=15),
            'subtype_id': self.ref('mail.mt_comment'),
            'reply_to': False,
            'body': 'Test follower',
        }, {
            'author_id': self.contact_2.id,
            'model': 'crm.lead',
            'res_id': self.lead_w_partner.id,
            'date': Datetime.now() - timedelta(days=29),
            'subtype_id': self.ref('mail.mt_comment'),
            'reply_to': False,
            'body': 'Test follower',
        }, {
            'author_id': self.contact_company.id,
            'model': 'crm.lead',
            'res_id': self.lead_w_email.id,
            'date': Datetime.now() - timedelta(days=35),
            'subtype_id': self.ref('mail.mt_comment'),
            'reply_to': False,
            'body': 'Test follower',
        }, {
            'author_id': self.contact_company.id,
            'model': 'crm.lead',
            'res_id': self.lead_w_partner.id,
            'date': Datetime.now(),
            'subtype_id': self.ref('mail.mt_comment'),
            'reply_to': False,
            'body': 'Test follower',
        }])
        initial_followers = self.lead_w_contact.message_follower_ids

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)
        master_lead = leads._merge_opportunity(max_length=None)

        self.assertEqual(master_lead, self.lead_w_contact)

        # Check followers of the destination lead
        new_partner_followers = (master_lead.message_follower_ids - initial_followers).partner_id
        self.assertIn(self.contact_2, new_partner_followers,
                      'The partner must follow the destination lead')
        # "contact_company" posted a message 35 days ago on lead_2, so it's considered as inactive
        # "contact_company" posted a message now on lead_3, but they don't follow lead_3
        # so this message is just ignored
        self.assertNotIn(self.contact_company, new_partner_followers,
                         'The partner was not active on the lead')
        self.assertIn(self.contact_1, master_lead.message_follower_ids.partner_id,
                      'Should not have removed follower of the destination lead')
