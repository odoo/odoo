from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.marketing_automation.models.marketing_activity import MarketingActivity
from odoo.addons.marketing_automation.models.marketing_participant import MarketingParticipant
from odoo.addons.marketing_automation.models.marketing_trace import MarketingTrace
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.tests.common import warmup
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('mail_performance', 'post_install', '-at_install')
class MAPerformanceCommon(BaseMailPerformance, TestMACommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date_reference = fields.Datetime.from_string("2024-07-15 10:30:00")

    @contextmanager
    def mockMACalls(self):
        original_act_execute_on_traces = MarketingActivity.execute_on_traces
        original_part_create = MarketingParticipant.create
        original_part_search = MarketingParticipant.search
        original_part_write = MarketingParticipant.write
        original_trace_create = MarketingTrace.create
        original_trace_search = MarketingTrace.search
        original_trace_write = MarketingTrace.write

        with patch.object(MarketingActivity, 'execute_on_traces',
                          autospec=True, side_effect=original_act_execute_on_traces) as mock_act_execute_on_traces, \
             patch.object(MarketingParticipant, 'create',
                          autospec=True, side_effect=original_part_create) as mock_part_create, \
             patch.object(MarketingParticipant, 'search',
                          autospec=True, side_effect=original_part_search) as mock_part_search, \
             patch.object(MarketingParticipant, 'write',
                          autospec=True, side_effect=original_part_write) as mock_part_write, \
             patch.object(MarketingTrace, 'create',
                          autospec=True, side_effect=original_trace_create) as mock_trace_create, \
             patch.object(MarketingTrace, 'search',
                          autospec=True, side_effect=original_trace_search) as mock_trace_search, \
             patch.object(MarketingTrace, 'write',
                          autospec=True, side_effect=original_trace_write) as mock_trace_write:
            self._mock_act_execute_on_traces = mock_act_execute_on_traces
            self._mock_part_create = mock_part_create
            self._mock_part_search = mock_part_search
            self._mock_part_write = mock_part_write
            self._mock_trace_create = mock_trace_create
            self._mock_trace_search = mock_trace_search
            self._mock_trace_write = mock_trace_write
            yield

    @classmethod
    def _create_test_campaign(cls, campaign_domain=None):
        # --------------------------------------------------
        # CAMPAIGN, based on marketing.test.performance
        #
        # ACT1           MAIL: begin, +1 hour
        #   ACT1_1       -> opened -> send an SMS after 1h with a promotional link
        #   ACT1_2       -> not_opened within 1 day-> update description through server action
        # ACT2           SMS: begin, +2 hour
        #   ACT2_1       -> clicked -> send an SMS after 1h with a promotional link
        #   ACT2_2       -> not_clicked within 1 day-> update description through server action
        # ACT3           WA: begin, +3 hour
        #   ACT3_1       -> replied -> send an SMS after 1h with a promotional link
        #   ACT3_2       -> not_replied within 1 day-> update description through server action
        # ACT4           SA: begin, +4 hour
        # --------------------------------------------------
        campaign_domain = campaign_domain or [("name", "!=", "Invalid")]
        test_campaign = cls.env['marketing.campaign'].with_user(cls.user_marketing_automation).create({
            "domain": campaign_domain,
            "model_id": cls.env['ir.model']._get_id("marketing.test.performance"),
            "name": "Test Campaign",
        })
        # ACT1: send a mailing
        act1_begin_mailing = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "email_from": cls.user_marketing_automation.email_formatted,
                "keep_archives": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )
        # ACT1_1: send an SMS 1 hour after 'open' event
        _act1_1_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: please confirm on https://test.example.com/confirm_mail",
                "mailing_type": "sms",
                "sms_allow_unsubscribe": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "parent_id": act1_begin_mailing.id,
                "trigger_type": "mail_open",
            },
        )
        # ACT_1_2: update description if not opened after 1 day
        # created by admin, should probably not give rights to marketing
        _act1_2_sa = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key1'})",
            act_values={
                "activity_domain": [("email_from", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": act1_begin_mailing.id,
                "trigger_type": "mail_not_open",
            },
        )

        # ACT2: send a SMS mailing
        act2_begin_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: mega promo on https://test.example.com/promo",
                "mailing_type": "sms",
                "keep_archives": True,
            },
            act_values={
                "interval_number": 2,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )
        # ACT2_1: send an SMS 1 hour after a 'click' event
        _act2_1_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: please confirm on https://test.example.com/confirm_sms",
                "mailing_type": "sms",
                "sms_allow_unsubscribe": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "parent_id": act2_begin_sms.id,
                "trigger_type": "sms_click",
            },
        )
        # ACT2_2: update description if not opened after 1 day
        _act2_2_sa = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key2'})",
            act_values={
                "activity_domain": [("phone", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": act2_begin_sms.id,
                "trigger_type": "sms_not_click",
            },
        )

        # ACT2: send a whatsapp
        act3_begin_wa = cls._create_activity_wa(
            test_campaign,
            template_values={
                'name': f'TestTemplate for {test_campaign.id}',
            },
            act_values={
                "interval_number": 3,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )
        # ACT3_1: send an SMS 1 hour after a 'replied' event
        _act3_1_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: please confirm on https://test.example.com/confirm_wa",
                "mailing_type": "sms",
                "sms_allow_unsubscribe": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "parent_id": act3_begin_wa.id,
                "trigger_type": "whatsapp_replied",
            },
        )
        # ACT3_2: update description if not replied after 1 day
        _act3_2_sa = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key3'})",
            act_values={
                "activity_domain": [("phone", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": act3_begin_wa.id,
                "trigger_type": "whatsapp_not_replied",
            },
        )

        # ACT4: run a SA
        _act4 = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key1'})",
            act_values={
                "interval_number": 4,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )

        return test_campaign

    @classmethod
    def _create_test_records(cls, count=200):
        # --------------------------------------------------
        # TEST RECORDS, using marketing.test.performance
        #
        # 200 times (or 'count')
        # - 3 records with partners
        # - 1 records wo partner, but email/mobile
        # - 1 record wo partner/email/mobile
        # AKA 1000 records
        # --------------------------------------------------
        return cls._create_marketauto_records(
            model="marketing.test.performance",
            count=count,
        )


@tagged('mail_performance', 'post_install', '-at_install')
class TestMAPerformance(MAPerformanceCommon):
    """ Simpler tests that do not require an heavy campaign in data """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_records = cls._create_test_records()

    def setUp(self):
        super().setUp()
        with self.mock_datetime_and_now(self.date_reference):
            self.test_campaign = self._create_test_campaign()
        self._launch_campaign(self.test_campaign, date_reference=self.date_reference)

    def test_assert_initial_values(self):
        """ Check initial values for tests """
        self.assertEqual(len(self.test_records), 1000)

        self.assertFalse(self.test_campaign.require_sync)
        self.assertEqual(self.test_campaign.last_sync_date, self.date_reference)
        self.assertEqual(
            len(self.test_campaign.marketing_activity_ids.trace_ids),
            len(self.test_records) * 4,
            "Should have generated one trace / begin activity / campaign record",
        )
        self.assertEqual(
            len(self.test_campaign.participant_ids),
            len(self.test_records),
            "Should have generated one participant / campaign record",
        )

    @warmup
    def test_campaign_sync_participants_launch(self):
        """ Test 'sync_participants' at campaign beginning. It is called by a
        cron regularly, or manually on campaign form view to start the campaign
        directly. It creates participants and their starting trace. """
        with self.mock_datetime_and_now(self.date_reference):
            campaign = self._create_test_campaign()
        self.assertEqual(len(self.test_records), 1000)

        # local: 1099
        # runbot: 1110, taking 100 more to avoid runbot issues in stable
        with self.assertQueryCount(1110 + 100), \
             self.mock_datetime_and_now(self.date_reference), \
             self.mockMACalls():
            campaign.sync_participants()

        # sanity check
        self.assertEqual(len(campaign.participant_ids), len(self.test_records))
        # performance check
        self.assertEqual(
            self._mock_part_create.call_count, 10,
            'Sync participants: created by batches of 100')
        self.assertEqual(self._mock_part_search.call_count, 0)
        self.assertEqual(self._mock_part_write.call_count, 1000,
                         'Sync participants: participants updated one by one,could be improved probably')
        self.assertEqual(self._mock_trace_create.call_count, 1000,
            'Sync participants: trace created one by one, could be improved')
        self.assertEqual(self._mock_trace_search.call_count, 0)
        self.assertEqual(self._mock_trace_write.call_count, 0)

    @mute_logger(
        'odoo.addons.mass_mailing_sms.models.mailing_mailing',
        'odoo.addons.mass_mailing.models.mailing',
    )
    @warmup
    def test_execute_activities_then_sync_participants(self):
        """ Test 'execute_activities' on all activity types. Then test
        'sync_participants' on a running campaign, aka updating participants
        based on DB state. """
        campaign = self.test_campaign

        # local: 15222
        # runbot: 15247, taking 100 more to avoid runbot issues in stable
        # hours+4 -> is going to trigger all 4 begin activities
        with self.assertQueryCount(15347), \
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=4)), \
             self.mock_mail_gateway(), self.mockSMSGateway(), \
             self.mockWhatsappGateway(), self.patchWhatsappCronTrigger(), \
             self.mockMACalls():
            campaign.execute_activities()

        # produced side records check
        self.assertEqual(
            len(self._new_mails), len(self.test_records),
            "Should have sent one email / campaign record, aka 1000",
        )
        self.assertEqual(
            len(self._new_sms), len(self.test_records),
            "Should have sent one SMS / campaign record, aka 1000",
        )
        self.assertEqual(
            len(self._new_wa_msg), len(self.test_records),
            "Should have sent one WA / campaign record, aka 1000",
        )
        self.assertEqual(
            len(campaign.marketing_activity_ids.trace_ids),
            len(self.test_records) * 10,
            "Should have: 4 begin activity + 6 sub activities / record, aka 10 * 1000",
        )
        # performance check
        self.assertEqual(self._mock_act_execute_on_traces.call_count, 8,
                         '4 activities * 2 batch / activity')
        self.assertEqual(self._mock_part_create.call_count, 0)
        self.assertEqual(self._mock_part_search.call_count, 0)
        self.assertEqual(self._mock_part_write.call_count, 8,
                         'Where do those come from anyway ?')
        self.assertEqual(self._mock_trace_create.call_count, 6000,
                         'Child trace creation: still done sequentially')
        self.assertEqual(self._mock_trace_search.call_count, 30,
                         'Yay 2*15. Probably because of batches inside batches. To check.')
        self.assertEqual(self._mock_trace_write.call_count, 1014,
                         'Where do those come from anyway ?')
        # side records performance check
        self.assertEqual(self.mail_mail_create_mocked.call_count, 20,
                         'Done by batch size inside activity execution batch (2 * 10)')
        self.assertEqual(self._mock_sms_create.call_count, 2,
                         'Done by activity execution batch (500 currently)')
        self.assertEqual(self._mock_wa_msg_create.call_count, 2,
                         'Done by activity execution batch (500 currently)')

        # now create 10*5 records, unlink other 50 records, observe performance
        self.test_records_new = self._create_test_records(count=10)
        self.assertEqual(len(self.test_records_new), 50)
        self.test_records[:50].unlink()

        # local: 74
        # runbot: 75, taking 10 more to avoid runbot issues in stable
        with self.assertQueryCount(85), \
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=24)), \
             self.mockMACalls():
            campaign.sync_participants()

        # sanity check
        self.assertEqual(
            len(campaign.participant_ids), 1050,
            'Removed records still have their participant, set as unlinked'
        )
        # performance check
        self.assertEqual(self._mock_part_create.call_count, 1)
        self.assertEqual(self._mock_part_search.call_count, 1)
        self.assertEqual(self._mock_part_write.call_count, 51)
        self.assertEqual(self._mock_trace_create.call_count, 50,
                         'Created sequentially')
        self.assertEqual(self._mock_trace_search.call_count, 1)
        self.assertEqual(self._mock_trace_write.call_count, 1)

    @users("user_marketing_automation")
    @warmup
    def test_update_participants(self):
        """ 'action_update_participants' can be called manually when the
        workflow has been modified on an ongoing marketing campaign. """
        campaign = self.test_campaign.with_env(self.env)

        # update activities, should update scheduled dates
        activity_mail = campaign.marketing_activity_ids.filtered(
            lambda a: a.trigger_type == "begin" and a.activity_type == "email"
        )
        self.assertTrue(activity_mail)
        activity_mail.write({
            "interval_number": 2,
        })

        # create new activities that are about to trigger the "require sync" flag !
        new_activity_begin = self._create_activity_mail(
            campaign,
            user=self.env.user,
            act_values={
                "interval_number": 1,
                "interval_type": "days",
                "name": "New begin MAIL activity",
                "trigger_type": "begin",
            },
        )
        _new_activity_sub = self._create_activity_sa(
            campaign,
            "records.write({'selection_field': 'key3'})",
            act_values={
                "activity_domain": [("email_from", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": new_activity_begin.id,
                "trigger_type": "mail_not_open",
            },
        )

        # local: 1055
        # runbot: 1055, taking 100 more to avoid runbot issues in stable
        with self.assertQueryCount(1155), \
             self.mockMACalls(), \
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=2)):
            campaign.action_update_participants()

        self.assertEqual(self._mock_part_create.call_count, 0)
        self.assertEqual(self._mock_part_search.call_count, 5)
        self.assertEqual(self._mock_part_write.call_count, 7)
        self.assertEqual(self._mock_trace_create.call_count, 1000,
                         'New traces for new begin activity created sequentially')
        self.assertEqual(self._mock_trace_search.call_count, 11)
        self.assertEqual(self._mock_trace_write.call_count, 1000,
                         'Looks like sequential update')
