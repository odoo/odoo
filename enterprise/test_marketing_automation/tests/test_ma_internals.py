# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.tests import tagged, users
from odoo.tools import mute_logger
from odoo.fields import Datetime


@tagged('marketing_automation')
class MarketingCampaignTest(TestMACommon):

    @classmethod
    def setUpClass(cls):
        super(MarketingCampaignTest, cls).setUpClass()
        cls.date_reference = Datetime.from_string('2023-11-08 08:00:00')
        cls.test_records = cls._create_marketauto_records(model='marketing.test.sms', count=2)
        cls.env['res.lang']._activate_lang('fr_FR')

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_campaign_archive(self):
        """ Ensures that campaigns are stopped when archived. """
        campaign = self.env['marketing.campaign'].create({
            'domain': [('id', 'in', self.test_records[0].ids)],
            'model_id': self.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'Test Campaign',
        })
        self._create_activity_mail(campaign, act_values={'interval_number': 0})

        self._launch_campaign(campaign)
        self.assertEqual(campaign.state, 'running')
        campaign.active = False
        self.assertEqual(campaign.state, 'stopped')

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.mail.models.mail_mail')
    def test_campaign_domain_with_translated_terms(self):
        """ Test that a campaign with a domain containing translated terms in
        the language of the responsible does correctly sync participant and
        execute activities. """
        # init test variables to ease code reading
        test_records = self.test_records.with_env(self.env)
        test_records_init = test_records.filtered(lambda r: r.name != 'Test_00')

        test_records.write({'text_trans': 'Test EN'})
        test_records.with_context(lang="fr_FR").write({'text_trans': 'Test FR'})

        self.env.user.sudo().write({'lang': 'en_US'})
        campaign = self.env['marketing.campaign'].create({
            'domain': [('name', '!=', 'Test_00'), ('text_trans', '=', 'Test FR')],
            'marketing_activity_ids': [
                (0, 0, {
                    'activity_type': 'email',
                    'name': 'Test',
                }),
            ],
            'model_id': self.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'Test Campaign',
        })

        # launch campaign, with responsible language != language terms in campaign domain
        self._launch_campaign(campaign, date_reference=self.date_reference)

        self.assertEqual(campaign.running_participant_count, 0)
        self.assertFalse(campaign.participant_ids)

        # with responsible language == language terms in campaign domain
        self.env.user.sudo().write({'lang': 'fr_FR'})
        with self.mock_datetime_and_now(self.date_reference):
            campaign.sync_participants()

        self.assertEqual(campaign.running_participant_count, len(test_records_init))
        self.assertEqual(campaign.participant_ids.mapped('res_id'), test_records_init.ids)
        self.assertEqual(set(campaign.participant_ids.mapped('state')), {'running'})

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_campaign_duplicate(self):
        """ The copy/duplicate of a campaign :
            - COPY activities, new activities related to the new campaign
            - DO NOT COPY the recipients AND the trace_ids AND the state (draft by default)
            - Normal Copy of other fields
            - Copy child of activity and keep coherence in parent_id
        """
        campaign = self.env['marketing.campaign'].create({
            'domain': [('id', 'in', self.test_records.ids)],
            'model_id': self.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'My First Campaign',
        })
        mailing = self._create_mailing('marketing.test.sms')
        activity = self._create_activity(
            campaign,
            mailing=mailing,
            name="ShouldDuplicate",
        )
        activity2 = self._create_activity(
            campaign,
            mailing=mailing,
            name="ShouldDuplicate2",
            parent_id=activity.id,
            trigger_type="mail_open",
        )

        self.assertEqual(
            self.env['marketing.activity'].search([('name', '=', "ShouldDuplicate")]),
            activity
        )

        self._launch_campaign(campaign)
        self.assertEqual(campaign.state, 'running')
        self.assertEqual(
            activity.trace_ids.mapped('participant_id'),
            campaign.participant_ids,
        )

        # copy campaign
        campaign2 = campaign.copy()

        # check campaign state
        self.assertEqual(campaign2.state, 'draft')
        self.assertEqual(campaign2.participant_ids, self.env['marketing.participant'])

        # activities: Two activities with similar name (one with an counter, the other without) but not related to the same campaign
        # see utm.mixin#_get_unique_names
        activities = self.env['marketing.activity'].search([('name', 'in', ('ShouldDuplicate', 'ShouldDuplicate [2]'))])
        activities2 = self.env['marketing.activity'].search([('name', 'in', ('ShouldDuplicate2', 'ShouldDuplicate2 [2]'))])
        activity_dup = campaign2.marketing_activity_ids.filtered(lambda activity: not activity.parent_id)
        activity2_dup = campaign2.marketing_activity_ids.filtered(lambda activity: activity.parent_id)
        self.assertEqual(activities, activity | activity_dup)
        self.assertEqual(activities2, activity2 | activity2_dup)
        self.assertEqual(activities.campaign_id, campaign | campaign2)
        self.assertEqual(activity_dup.trace_ids, self.env['marketing.trace'])
        self.assertEqual(activity2_dup.trace_ids, self.env['marketing.trace'])
        self.assertEqual(campaign2.marketing_activity_ids, activity_dup | activity2_dup)

        # check relationships
        self.assertEqual(activity2.parent_id, activity)
        self.assertEqual(activity2_dup.parent_id, activity_dup)

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_campaign_participants_compute(self):
        """Check that the participant count compute method works."""
        empty_campaign = self.env['marketing.campaign'].create({
            'name': 'My First Campaign',
            'model_id': self.env['ir.model']._get('marketing.test.sms').id,
        })
        self.assertEqual(empty_campaign.total_participant_count, 0)

        campaign1 = self.env['marketing.campaign'].create({
            'name': 'Campaign 1',
            'model_id': self.env['ir.model']._get('marketing.test.sms').id,
        })
        campaign2 = self.env['marketing.campaign'].create({
            'name': 'Campaign 2',
            'model_id': self.env['ir.model']._get('marketing.test.sms').id,
        })
        self.env['marketing.participant'].create([
            {'campaign_id': campaign1.id, 'state': 'running', 'is_test': True},
            {'campaign_id': campaign1.id, 'state': 'running', 'is_test': True},
            {'campaign_id': campaign1.id, 'state': 'running', 'is_test': False},
            {'campaign_id': campaign1.id, 'state': 'running', 'is_test': False},
            {'campaign_id': campaign1.id, 'state': 'completed', 'is_test': True},
            {'campaign_id': campaign1.id, 'state': 'completed', 'is_test': False},
            {'campaign_id': campaign2.id, 'state': 'running', 'is_test': True},
            {'campaign_id': campaign2.id, 'state': 'completed', 'is_test': True},
            {'campaign_id': campaign2.id, 'state': 'completed', 'is_test': False},
            {'campaign_id': campaign2.id, 'state': 'completed', 'is_test': False},
        ])
        self.assertEqual(campaign1.running_participant_count, 2)
        self.assertEqual(campaign1.completed_participant_count, 1)
        self.assertEqual(campaign1.total_participant_count, 3)
        self.assertEqual(campaign1.test_participant_count, 3)

        self.assertEqual(campaign2.running_participant_count, 0)
        self.assertEqual(campaign2.completed_participant_count, 2)
        self.assertEqual(campaign2.total_participant_count, 2)
        self.assertEqual(campaign2.test_participant_count, 2)

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_campaign_unique_field(self):
        # initial data: 0-1-2 have unique partners, 3-4 are void, 4 will receive same partner as 0 to test uniqueness
        test_records = self.test_records[:5]
        self.assertEqual(len(test_records), 5)
        test_records[-1].write({'name': test_records[0].name})

        name_field = self.env['ir.model.fields'].sudo().search([
            ('model_id', '=', self.env['ir.model']._get_id('marketing.test.sms')),
            ('name', '=', 'name')
        ])

        campaign = self.env['marketing.campaign'].create({
            'domain': [('id', 'in', test_records.ids)],
            'model_id': self.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'My First Campaign',
            'unique_field_id': name_field.id,
        })
        mailing = self._create_mailing('marketing.test.sms')
        _activity = self._create_activity(campaign, mailing=mailing)

        self._launch_campaign(campaign)
        self.assertEqual(campaign.running_participant_count, 4)
        self.assertEqual(campaign.participant_ids.mapped('res_id'), test_records[:4].ids)

        test_records[-1].write({'name': 'Unique Again'})
        campaign.sync_participants()

        self.assertEqual(campaign.running_participant_count, 5)
        self.assertEqual(campaign.participant_ids.mapped('res_id'), test_records.ids)

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_campaign_unique_field_many2one(self):
        # initial data: 0-1-2 have unique partners, 3-4 are void, 4 will receive same partner as 0 to test uniqueness
        test_records = self.test_records[:5]
        self.assertEqual(len(test_records), 5)
        self.assertEqual(len(test_records.mapped('customer_id')), 3)
        test_records[-1].write({'customer_id': test_records[0].customer_id.id})
        self.assertEqual(test_records[3].customer_id, self.env['res.partner'])

        partner_field = self.env['ir.model.fields'].sudo().search([
            ('model_id', '=', self.env['ir.model']._get_id('marketing.test.sms')),
            ('name', '=', 'customer_id')
        ])

        campaign = self.env['marketing.campaign'].create({
            'domain': [('id', 'in', test_records.ids)],
            'model_id': self.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'My First Campaign',
            'unique_field_id': partner_field.id,
        })
        mailing = self._create_mailing('marketing.test.sms')
        _activity = self._create_activity(campaign, mailing=mailing)

        self._launch_campaign(campaign)
        self.assertEqual(campaign.running_participant_count, 3)
        self.assertEqual(campaign.participant_ids.mapped('res_id'), test_records[0:3].ids)

        # new partner -> will be added to set of participants as not duplicated anymore
        test_records[-1].write({'customer_id': self.env['res.partner'].create({'name': 'JustHere'})})
        campaign.sync_participants()

        self.assertEqual(campaign.running_participant_count, 4)
        self.assertEqual(campaign.participant_ids.mapped('res_id'), (test_records[0:3] | test_records[-1]).ids)
