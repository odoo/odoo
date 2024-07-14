# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.marketing_automation.tests.common import MarketingAutomationCommon
from odoo.fields import Datetime
from odoo.tests import tagged, users
from odoo.tools import mute_logger


class SyncingCase(MarketingAutomationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date_reference = Datetime.from_string('2023-11-08 09:00:00')
        cls.activity_1 = cls._create_activity_mail(
            cls.campaign,
            user=cls.user_marketing_automation,
            act_values={
                'create_date': cls.date_reference - timedelta(days=1),
                'trigger_type': 'begin',
                'interval_number': 1, 'interval_type': 'hours',
            },
        )
        cls.activity_2 = cls._create_activity_mail(
            cls.campaign,
            user=cls.user_marketing_automation,
            act_values={
                'create_date': cls.date_reference - timedelta(days=1),
                'parent_id': cls.activity_1.id,
                'trigger_type': 'activity',
                'interval_number': 1, 'interval_type': 'hours',
            },
        )
        cls.env.flush_all()


@tagged('marketing_automation')
class TestDuplicate(SyncingCase):
    """ Test workflow when having duplicate participants or traces. This may
    happen in several occasions, and we should be defensive with duplicates. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.participants = cls.env['marketing.participant'].create([
            {
                'campaign_id': cls.campaign.id,
                'res_id': record.id,
                'state': 'running',
            }
            for record in cls.test_contacts[:2]
            for idx in range(2)
        ])
        cls.traces = cls.env['marketing.trace'].create([
            {
                'activity_id': cls.activity_1.id,
                'participant_id': participant.id,
                'state': state,
            }
            for participant, states in zip(
                cls.participants,
                (['scheduled', 'processed'], ['canceled', 'processed'],  # record 0
                 ['scheduled', 'processed'], ['processed', 'processed'],  # record 1
                )
            )
            for state in states
        ])
        cls.mailing_traces = cls.env['mailing.trace'].create([
            {
                'marketing_trace_id': trace.id,
                'model': cls.campaign.model_name,
                'res_id': trace.res_id,
                'sent_datetime': sent_dt,
                'trace_status': trace_status,
                'trace_type': 'mail',
            }
            for trace, (sent_dt, trace_status) in zip(
                cls.traces,
                [
                    # record 0
                    (False, 'outgoing'),
                    (cls.date_reference, 'sent'),
                    (cls.date_reference, 'bounce'),
                    (False, 'error'),
                    # record 1
                    (False, 'outgoing'),
                    (cls.date_reference, 'sent'),
                    (cls.date_reference, 'cancel'),
                    (False, 'error'),
                ]
            )
        ])
        cls.env.flush_all()

    @users('user_marketing_automation')
    def test_statistics(self):
        """ In case of multiple participants / multiple traces per record
        (manual update, unwanted duplication) we may have more traces than
        target records. We consider it is ok, and prefer keeping statistics
        highlighting a potential issue compared to trying to guess a 'mean'
        trace statistics. """
        campaign = self.campaign.with_env(self.env)
        activity_1 = self.activity_1.with_env(self.env)

        # campaign statistics
        self.assertEqual(campaign.running_participant_count, 4)

        # activity statistics
        self.assertEqual(activity_1.processed, 5)
        self.assertEqual(activity_1.rejected, 0)
        self.assertEqual(activity_1.total_bounce, 1)
        self.assertEqual(activity_1.total_click, 0)
        self.assertEqual(activity_1.total_open, 0)
        self.assertEqual(activity_1.total_reply, 0)
        self.assertEqual(activity_1.total_sent, 4)


@tagged('marketing_automation')
class TestSyncing(SyncingCase):
    """ Test various cases of synchronization, notably to avoid creating
    duplicate traces. """

    @users('user_marketing_automation')
    def test_activity_require_sync(self):
        """ Test activity and campaign 'require_sync' field, as well as campaign
        'last_sync_date' behavior """
        campaign = self.campaign.with_env(self.env)
        activity = self.activity_1.with_env(self.env)

        # starting campaign just changes the state, nothing on sync
        campaign.action_start_campaign()
        self.assertFalse(activity.require_sync)
        self.assertFalse(campaign.last_sync_date)
        self.assertFalse(campaign.require_sync)

        # changing time info should update require sync flag
        activity.interval_number = 3
        self.assertTrue(activity.require_sync)
        self.assertFalse(campaign.require_sync, 'Campaign without sync date is never "To Sync"')
        campaign.last_sync_date = self.date_reference - timedelta(days=2)
        self.assertTrue(campaign.require_sync)

        # reset require_sync, update time info again
        activity.require_sync = False
        self.assertFalse(campaign.require_sync)
        activity.interval_type = "weeks"
        self.assertTrue(activity.require_sync)
        self.assertTrue(campaign.require_sync)

        # manually set as synchronized
        with self.mock_datetime_and_now(self.date_reference):
            campaign.action_set_synchronized()
        self.assertFalse(activity.require_sync)
        self.assertEqual(campaign.last_sync_date, self.date_reference)
        self.assertFalse(campaign.require_sync)

    @mute_logger('odoo.addons.mass_mailing.models.mailing', 'odoo.tests')
    def test_activity_schedule_date(self):
        """ Test updating participants in a running campaign, check schedule
        date is set based on trigger type / parent. """
        marketing_campaign = self.env['marketing.campaign'].create({
            'domain': [('id', 'in', self.test_contacts.ids)],
            'model_id': self.env['ir.model']._get_id(self.test_contacts._name),
            'name': 'My First Campaign',
        })
        parent_activity = self._create_activity_mail(marketing_campaign)
        child_activity = self._create_activity_mail(
            marketing_campaign,
            act_values={
                'parent_id': parent_activity.id,
                'trigger_type': 'mail_open',
            },
        )

        marketing_campaign.action_start_campaign()
        marketing_campaign.sync_participants()
        with self.mock_datetime_and_now(self.date_reference):
            [trace.action_execute() for trace in parent_activity.trace_ids]
        self.assertEqual(len(child_activity.trace_ids), len(self.test_contacts))

        child_activity.update({
            'interval_type': 'days',
            'interval_number': 5,
        })
        marketing_campaign.action_update_participants()

        expected_schedule_date = self.date_reference + timedelta(days=5)
        for trace in child_activity.trace_ids:
            self.assertEqual(trace.schedule_date, expected_schedule_date)

    @users('user_marketing_automation')
    def test_assert_initial_values(self):
        """ Test initial values to have a common ground for other tests """
        campaign = self.campaign.with_env(self.env)
        self.assertFalse(campaign.last_sync_date)
        self.assertEqual(campaign.mass_mailing_count, 2)
        self.assertFalse(campaign.require_sync)
        # activities
        for activity in campaign.marketing_activity_ids:
            self.assertEqual(activity.create_date, self.date_reference - timedelta(days=1))
            self.assertFalse(activity.require_sync)
        # participants
        self.assertFalse(campaign.participant_ids)
        self.assertEqual(campaign.running_participant_count, 0)
        self.assertEqual(campaign.completed_participant_count, 0)
        self.assertEqual(campaign.total_participant_count, 0)
        self.assertEqual(campaign.test_participant_count, 0)

    @users('user_marketing_automation')
    def test_campaign_action_update_participants_no_last_sync_date(self):
        """ Test 'action_update_participants' that should not crash when campaign
        has no 'last_sync_date'; should skip actually. """
        campaign = self.campaign.with_env(self.env)
        self.assertFalse(campaign.last_sync_date)

        with self.mock_datetime_and_now(self.date_reference):
            campaign.action_update_participants()
        self.assertEqual(campaign.last_sync_date, self.date_reference)
        self.assertFalse(campaign.participant_ids)
        # should not have any traces
        self.assertActivityWoTrace(self.activity_1 + self.activity_2)

    @users('user_marketing_automation')
    def test_campaign_copy_dupes(self):
        """ Test copy of campaign, should not lead to duplicating traces due
        to bad synchronization propagation. """
        # generate participants
        campaign = self.campaign.with_env(self.env)
        with self.mock_datetime_and_now(self.date_reference):
            campaign.sync_participants()
        self.assertEqual(len(campaign.participant_ids), len(self.test_contacts))

        # copy campaign: should not generate duplicates
        with self.mock_datetime_and_now(self.date_reference + timedelta(days=1)):
            new_campaign = campaign.copy()
            new_campaign.action_start_campaign()
        self.assertFalse(new_campaign.last_sync_date, "Copying a campaign should not copy its sync date")
        self.assertEqual(len(new_campaign.marketing_activity_ids), 2)
        new_activity_1 = new_campaign.marketing_activity_ids.filtered(
            lambda a: a.trigger_type == 'begin'
        )
        new_activity_2 = new_campaign.marketing_activity_ids.filtered(
            lambda a: a.trigger_type != 'begin'
        )
        # should not have any traces
        self.assertActivityWoTrace(new_activity_1 + new_activity_2)

        # launch duplicated campaign participants and update: should not generate
        # duplicate traces (notably due to old sync date of campaign)
        with self.mock_datetime_and_now(self.date_reference + timedelta(days=1)):
            new_campaign.sync_participants()
            new_campaign.action_update_participants()

        # should generate traces for 'begin' activity
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts,
                'status': 'scheduled',
            }],
            new_activity_1,
        )
        # should not generate traces for other activities
        self.assertActivityWoTrace(new_activity_2)

    @users('user_marketing_automation')
    def test_campaign_sync_participants(self):
        """ Test 'sync_participants' that should create participants, and create
        traces for beginning activities. """
        # generate participants
        campaign = self.campaign.with_env(self.env)
        with self.mock_datetime_and_now(self.date_reference):
            campaign.sync_participants()

        # 'sync_participants': creates participant / record, with a trace for begin
        # activity only (other traces will be created at process time)
        self.assertEqual(campaign.last_sync_date, self.date_reference)
        self.assertEqual(len(campaign.participant_ids), len(self.test_contacts))
        # should generate traces for 'begin' activity
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts,
                'status': 'scheduled',
            }],
            self.activity_1,
        )
        # should not generate traces for other activities
        self.assertActivityWoTrace(self.activity_2)

    @users('user_marketing_automation')
    def test_participants_creation_dupes(self):
        """ This test may fail randomly based on time if not launched with
        fix in 'action_update_participants' : comparing activity.create_date
        with campaign.last_sync_date may fail as the first one comes from
        sql NOW, second one from datetime.now . We don't want duplicates
        marketing traces hence having to be tolerant on date check. """
        campaign = self.env['marketing.campaign'].create({
            'domain': [('id', '=', self.test_contacts[0].id)],
            'model_id': self.env['ir.model']._get_id(self.test_contacts._name),
            'marketing_activity_ids': [
                (0, 0, {
                    'activity_type': 'email',
                    'name': 'Test Activity',
                    'trigger_type': 'begin',
                }),
            ],
            'name': 'Test Participant Dupes',
        })
        campaign.sync_participants()

        # execute immediately (same second as the creation)
        # because of that condition (precision is second)
        # >>> a.create_date >= campaign.last_sync_date
        campaign.action_update_participants()

        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts[0],
                'status': 'scheduled',
            }],
            campaign.marketing_activity_ids,
        )

    @users('user_marketing_automation')
    def test_participants_creation_then_update_dupes(self):
        """ Test participants creation then update when adding new activities
        on a running campaign. We should not duplicate traces, notably when
        a participant had traces on a new activity that is then updated
        automatically. """
        campaign = self.campaign.with_env(self.env)

        # init participants and traces
        with self.mock_datetime_and_now(self.date_reference):
            campaign.action_start_campaign()
            campaign.sync_participants()
            campaign.action_update_participants()

        # should be initialized with test data
        self.assertEqual(len(campaign.participant_ids), len(self.test_contacts))
        # should generate traces for 'begin' activity
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts,
                'status': 'scheduled',
            }],
            self.activity_1,
        )
        # should not generate traces for other activities
        self.assertActivityWoTrace(self.activity_2)

        # add a new begin activity, and a child to activity_1
        new_activity_begin = self._create_activity_mail(
            campaign,
            user=self.user_admin,
            act_values={
                'create_date': self.date_reference + timedelta(hours=1),
                'trigger_type': 'begin',
                'interval_number': 1, 'interval_type': 'hours',
            },
        )
        new_activity_mail = self._create_activity_mail(
            campaign,
            user=self.env.user,
            act_values={
                'create_date': self.date_reference + timedelta(hours=1),
                'parent_id': self.activity_1.id,
                'trigger_type': 'mail_open',
                'interval_number': 0,
            },
        )
        for activity in new_activity_begin + new_activity_mail:
            self.assertEqual(activity.create_date, self.date_reference + timedelta(hours=1))
        self.assertEqual(campaign.last_sync_date, self.date_reference)
        self.assertTrue(campaign.require_sync, 'Campaign should require a sync due to new activity')

        # add a new participant
        new_record = self.env['mailing.contact'].create({
            'email': 'ma.test.new.1@example.com',
            'name': 'MATest_new_1',
        })
        with self.mock_datetime_and_now(self.date_reference + timedelta(hours=2)):
            campaign.sync_participants()

        # should have generated one trace / begin activity for the new participant
        self.assertEqual(len(campaign.participant_ids), len(self.test_contacts) + 1)
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts + new_record,
                'status': 'scheduled',
            }],
            self.activity_1,
        )
        self.assertMarketAutoTraces(
            [{
                'records': new_record,
                'status': 'scheduled',
            }],
            new_activity_begin,
        )
        self.assertActivityWoTrace(new_activity_mail)

        # run first activity
        with self.mock_datetime_and_now(self.date_reference + timedelta(hours=3)), self.mock_mail_gateway():
            campaign.execute_activities()
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts + new_record,
                'status': 'processed',
                'trace_status': 'sent',
            }],
            self.activity_1,
        )
        self.assertMarketAutoTraces(
            [{
                'records': new_record,
                'status': 'processed',
                'mail_values': {
                    'email_from': self.user_admin.email_formatted,
                },
                'trace_status': 'sent',
            }],
            new_activity_begin,
        )
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts + new_record,
                'status': 'scheduled',
            }],
            new_activity_mail,
        )

        # campaign should require an update, update it
        self.assertTrue(campaign.require_sync, 'Campaign should require an update')
        with self.mock_datetime_and_now(self.date_reference + timedelta(hours=4)):
            campaign.action_update_participants()
        # should have synchronized traces for all participants / all begin activities
        # without dupes for the new_record (already had one, don't create again)
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts + new_record,
                'status': 'processed',
                'trace_status': 'sent',
            }],
            self.activity_1,
        )
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts,
                'status': 'scheduled',
            }, {
                'records': new_record,
                'status': 'processed',
                'mail_values': {
                    'email_from': self.user_admin.email_formatted,
                },
                'trace_status': 'sent',
            }],
            new_activity_begin,
        )
        self.assertMarketAutoTraces(
            [{
                'records': self.test_contacts + new_record,
                'status': 'scheduled',
            }],
            new_activity_mail,
        )
