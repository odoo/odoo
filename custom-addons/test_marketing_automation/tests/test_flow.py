# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.fields import Datetime
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('marketing_automation')
class TestMarketAutoFlow(TestMACommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super(TestMarketAutoFlow, cls).setUpClass()
        cls.date_reference = Datetime.from_string('2014-08-01 15:02:32')  # so long, little task
        cls.env['res.lang']._activate_lang('fr_FR')

        # --------------------------------------------------
        # TEST RECORDS, using marketing.test.sms (customers)
        #
        # 2 times
        # - 3 records with partners
        # - 1 records wo partner, but email/mobile
        # - 1 record wo partner/email/mobile
        # 1 wrong email
        # 1 duplicate)
        # --------------------------------------------------
        cls.test_records_base = cls._create_marketauto_records(model='marketing.test.sms', count=2)
        cls.test_records_failure = cls.env['marketing.test.sms'].create([
            {
                'email_from': 'wrong',
                'mobile': '0455990000',
                'name': 'Wrong Email',
            }, {
                'email_from': cls.test_records_base[1].email_from,
                'mobile': cls.test_records_base[1].mobile,
                # compared to < 17, we need the name to be the same, as duplicate
                # comparison is now done on sent content + recipient, not just
                # the recipient itself
                'name': cls.test_records_base[1].name,
            },
        ])
        (cls.test_records_failure_wrong, cls.test_records_failure_dupe) = cls.test_records_failure
        cls.test_records = cls.test_records_base + cls.test_records_failure

        # --------------------------------------------------
        # CAMPAIGN, based on marketing.test.sms (customers)
        #
        # ACT1           MAIL mailing
        #   ACT2.1       -> reply -> send an SMS after 1h with a promotional link
        #     ACT3.1       -> sms_click -> send a confirmation SMS right at click
        #   ACT2.2       -> not opened within 1 day-> update description through server action
        # --------------------------------------------------

        cls.campaign = cls.env['marketing.campaign'].with_user(cls.user_marketing_automation).create({
            'domain': [('name', '!=', 'Invalid')],
            'model_id': cls.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'Test Campaign',
        })
        # first activity: send a mailing
        cls.act1_mailing = cls._create_mailing(
            'marketing.test.sms',
            email_from=cls.user_marketing_automation.email_formatted,
            keep_archives=True,
        ).with_user(cls.user_marketing_automation)
        cls.act1 = cls._create_activity(
            cls.campaign,
            mailing=cls.act1_mailing,
            trigger_type='begin',
            interval_number=0,
        ).with_user(cls.user_marketing_automation)

        # second activity: send an SMS 1 hour after a reply
        cls.act2_1_mailing = cls._create_mailing(
            'marketing.test.sms',
            mailing_type='sms',
            body_plaintext='SMS for {{ object.name }}: mega promo on https://test.example.com',
            sms_allow_unsubscribe=True,
        ).with_user(cls.user_marketing_automation)
        cls.act2_1 = cls._create_activity(
            cls.campaign,
            mailing=cls.act2_1_mailing,
            parent_id=cls.act1.id,
            trigger_type='mail_reply',
            interval_number=1, interval_type='hours',
        ).with_user(cls.user_marketing_automation)
        # other activity: update description if not opened after 1 day
        # created by admin, should probably not give rights to marketing
        cls.act2_2_sact = cls.env['ir.actions.server'].create({
            'code': """
for record in records:
    record.write({'description': record.description + ' - Did not answer, sad campaign is sad.'})""",
            'model_id': cls.env['ir.model']._get('marketing.test.sms').id,
            'name': 'Update description',
            'state': 'code',
        })
        cls.act2_2 = cls._create_activity(
            cls.campaign,
            action=cls.act2_2_sact,
            parent_id=cls.act1.id,
            trigger_type='mail_not_open',
            interval_number=1, interval_type='days',
            activity_domain=[('email_from', '!=', False)],
        ).with_user(cls.user_marketing_automation)

        cls.act3_1_mailing = cls._create_mailing(
            'marketing.test.sms',
            mailing_type='sms',
            body_plaintext='Confirmation for {{ object.name }}',
            sms_allow_unsubscribe=False,
        ).with_user(cls.user_marketing_automation)
        cls.act3_1 = cls._create_activity(
            cls.campaign,
            mailing=cls.act3_1_mailing,
            parent_id=cls.act2_1.id,
            trigger_type='sms_click',
            interval_number=0,
        ).with_user(cls.user_marketing_automation)

        cls.env.flush_all()

    def test_assert_initial_values(self):
        """ Test initial values to have a common ground for other tests """
        # ensure initial data
        self.assertEqual(len(self.test_records), 12)
        self.assertEqual(len(self.test_records.filtered(lambda r: r.name != 'Test_00')), 11)
        self.assertEqual(self.campaign.state, 'draft')

    @mute_logger('odoo.addons.base.models.ir_model',
                 'odoo.addons.mail.models.mail_mail',
                 'odoo.addons.mass_mailing.models.mailing',
                 'odoo.addons.mass_mailing_sms.models.mailing_mailing')
    @users('user_marketing_automation')
    def test_marketing_automation_flow(self):
        """ Test a marketing automation flow involving several steps. """
        # init test variables to ease code reading
        date_reference = self.date_reference
        test_records = self.test_records.with_user(self.env.user)
        test_records_init = test_records.filtered(lambda r: r.name != 'Test_00')

        # update campaign
        act1 = self.act1.with_user(self.env.user)
        act2_1 = self.act2_1.with_user(self.env.user)
        act2_2 = self.act2_2.with_user(self.env.user)
        act3_1 = self.act3_1.with_user(self.env.user)
        campaign = self.campaign.with_user(self.env.user)
        campaign.write({
            'domain': [('name', '!=', 'Test_00')],
        })

        # CAMPAIGN START
        # ------------------------------------------------------------

        # User starts and syncs its campaign
        with freeze_time(self.date_reference), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers:
            campaign.action_start_campaign()
        self.assertEqual(campaign.state, 'running')

        # a cron.trigger has been created to sync participants after campaign start
        self.assertEqual(len(captured_triggers.records), 1)
        self.assertEqual(
            captured_triggers.records[0].cron_id,
            self.env.ref('marketing_automation.ir_cron_campaign_sync_participants'))
        self.assertEqual(captured_triggers.records[0].call_at, self.date_reference)

        with freeze_time(date_reference), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            campaign.sync_participants()

        # All records not containing Test_00 should be added as participants
        self.assertEqual(campaign.running_participant_count, len(test_records_init))
        self.assertEqual(
            set(campaign.participant_ids.mapped('res_id')),
            set(test_records_init.ids)
        )
        self.assertEqual(
            set(campaign.participant_ids.mapped('state')),
            set(['running'])
        )

        # Beginning activity should contain a scheduled trace for each participant
        self.assertMarketAutoTraces(
            [{
                'status': 'scheduled',
                'records': test_records_init,
                'participants': campaign.participant_ids,
                'fields_values': {
                    'schedule_date': date_reference,
                },
            }],
            act1,
        )

        # a cron.trigger has been created to execute activities after campaign start
        # there should only be one since we have 9 activities with the same scheduled_date
        self.assertEqual(len(captured_triggers.records), 1)
        self.assertEqual(
            captured_triggers.records[0].cron_id,
            self.env.ref('marketing_automation.ir_cron_campaign_execute_activities'))
        self.assertEqual(captured_triggers.records[0].call_at, self.date_reference)

        # No other trace should have been created as the first one are waiting to be processed
        self.assertEqual(act2_1.trace_ids, self.env['marketing.trace'])
        self.assertEqual(act2_2.trace_ids, self.env['marketing.trace'])
        self.assertEqual(act3_1.trace_ids, self.env['marketing.trace'])

        # ACT1: LAUNCH MAILING
        # ------------------------------------------------------------
        test_records_1_ko = test_records_init.filtered(
            lambda r: not r.email_from or r.email_from == 'wrong'
        ) + self.test_records_failure_dupe
        test_records_1_ok = test_records_init.filtered(lambda r: r not in test_records_1_ko)

        # First traces are processed, emails are sent (or failed)
        with freeze_time(self.date_reference), \
             self.mock_mail_gateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            campaign.execute_activities()

        self.assertMarketAutoTraces(
            [{
                'status': 'processed',
                'records': test_records_1_ok,
                'trace_status': 'sent',
                'fields_values': {
                    'schedule_date': date_reference,
                },
            }, {
                'status': 'canceled',
                'records': self.test_records_failure_wrong,
                'fields_values': {
                    'schedule_date': date_reference,
                    'state_msg': 'Email canceled',
                },
                # wrong email -> trace set as ignored
                'trace_email': self.test_records_failure_wrong.email_from,
                'trace_failure_type': 'mail_email_invalid',
                'trace_status': 'cancel',
            }, {
                'status': 'canceled',
                'records': self.test_records_failure_dupe,
                'fields_values': {
                    'schedule_date': date_reference,
                    'state_msg': 'Email canceled',
                },
                # wrong email -> trace set as ignored
                'trace_email': self.test_records_failure_dupe.email_normalized,
                'trace_failure_type': 'mail_dup',
                'trace_status': 'cancel',
            }, {
                'status': 'canceled',
                'records': (test_records_1_ko - self.test_records_failure_wrong - self.test_records_failure_dupe),
                'fields_values': {
                    'schedule_date': date_reference,
                    'state_msg': 'Email canceled',
                },
                # no email -> trace set as ignored
                'trace_failure_type': 'mail_email_missing',
                'trace_status': 'cancel',
            }],
            act1,
        )

        # Child traces should have been generated for all traces of parent activity as activity_domain
        # is taken into account at processing, not generation (see act2_2)
        self.assertMarketAutoTraces(
            [{
                'status': 'scheduled',
                'records': test_records_init,
                'participants': campaign.participant_ids,
                'fields_values': {
                    'schedule_date': False,
                },
            }],
            act2_1,
        )
        self.assertMarketAutoTraces(
            [{
                'status': 'scheduled',
                'records': test_records_init,
                'participants': campaign.participant_ids,
                'fields_values': {
                    'schedule_date': date_reference + relativedelta(days=1),
                },
            }],
            act2_2,
        )

        # a cron.trigger has been created to execute activities 1 day after mailing is sent
        # there should only be one since we have 9 activities with the same scheduled_date
        self.assertEqual(1, len(captured_triggers.records))
        captured_trigger = captured_triggers.records[0]
        self.assertEqual(
            self.env.ref('marketing_automation.ir_cron_campaign_execute_activities'),
            captured_trigger.cron_id)
        self.assertEqual(self.date_reference + relativedelta(days=1), captured_trigger.call_at)

        # Processing does not change anything (not time yet)
        with freeze_time(self.date_reference):
            campaign.execute_activities()
        self.assertEqual(set(act2_1.trace_ids.mapped('state')), set(['scheduled']))
        self.assertEqual(set(act2_2.trace_ids.mapped('state')), set(['scheduled']))

        # ACT1 FOLLOWUP: PROCESS SOME REPLIES (+1 H)
        # ------------------------------------------------------------

        date_reference_reply = date_reference + relativedelta(hours=1)
        test_records_1_replied = test_records_1_ok[:2]
        with freeze_time(date_reference_reply), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            for record in test_records_1_replied:
                self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, record)

        self.assertMarketAutoTraces(
            [{
                'status': 'processed',
                'records': test_records_1_replied,
                'trace_status': 'reply',
                'fields_values': {
                    'schedule_date': date_reference,
                },
            }, {
                'status': 'processed',
                'records': test_records_1_ok - test_records_1_replied,
                'trace_status': 'sent',
                'fields_values': {
                    'schedule_date': date_reference,
                },
            }, {
                'status': 'canceled',
                'records': self.test_records_failure_wrong,
                'fields_values': {
                    'schedule_date': date_reference,
                    'state_msg': 'Email canceled',
                },
                # wrong email -> trace set as ignored
                'trace_email': self.test_records_failure_wrong.email_from,
                'trace_failure_type': 'mail_email_invalid',
                'trace_status': 'cancel',
            }, {
                'status': 'canceled',
                'records': self.test_records_failure_dupe,
                'fields_values': {
                    'schedule_date': date_reference,
                    'state_msg': 'Email canceled',
                },
                # wrong email -> trace set as ignored
                'trace_email': self.test_records_failure_dupe.email_normalized,
                'trace_failure_type': 'mail_dup',
                'trace_status': 'cancel',
            }, {
                'status': 'canceled',
                'records': (test_records_1_ko - self.test_records_failure_wrong - self.test_records_failure_dupe),
                'fields_values': {
                    'schedule_date': date_reference,
                    'state_msg': 'Email canceled',
                },
                # no email -> trace set as ignored
                'trace_failure_type': 'mail_email_missing',
                'trace_status': 'cancel',
            }],
            act1,
        )

        # Replied records -> SMS scheduled
        self.assertMarketAutoTraces(
            [{
                'status': 'scheduled',
                'records': test_records_1_replied,
                'fields_values': {
                    'schedule_date': date_reference_reply + relativedelta(hours=1),
                },
            }, {
                'status': 'scheduled',
                'records': test_records_init - test_records_1_replied,
                'fields_values': {
                    'schedule_date': False,
                },
            }],
            act2_1,
        )
        # Replied records -> mail_not_open canceled
        self.assertMarketAutoTraces(
            [{
                'status': 'scheduled',
                'records': test_records_init - test_records_1_replied,
                'fields_values': {
                    'schedule_date': date_reference + relativedelta(days=1),
                },
            }, {
                'status': 'canceled',
                'records': test_records_1_replied,
                'fields_values': {
                    'schedule_date': date_reference_reply,
                },
            }],
            act2_2,
        )

        # a cron.trigger has been created after each separate reply exactly 1 hour after the reply
        # to match the created marketing.trace (ACT2.1)
        # (here we have 2 replies considered at the exact same time but real use cases will most
        # likely not)
        self.assertEqual(len(captured_triggers.records), 2)
        for captured_trigger in captured_triggers.records:
            self.assertEqual(
                captured_trigger.cron_id,
                self.env.ref('marketing_automation.ir_cron_campaign_execute_activities'))
            self.assertEqual(captured_trigger.call_at, date_reference_reply + relativedelta(hours=1))

        # ACT2_1: REPLIED GOT AN SMS (+2 H)
        # ------------------------------------------------------------

        date_reference_new = date_reference + relativedelta(hours=2)

        with freeze_time(date_reference_new), \
             self.mockSMSGateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            campaign.execute_activities()

        self.assertMarketAutoTraces(
            [{
                'status': 'processed',
                'records': test_records_1_replied,
                'fields_values': {
                    'schedule_date': date_reference_reply + relativedelta(hours=1),
                },
                'trace_status': 'outgoing',
            }, {
                'status': 'scheduled',
                'records': test_records_init - test_records_1_replied,
                'fields_values': {
                    'schedule_date': False,
                },
            }],
            act2_1,
        )
        self.assertMarketAutoTraces(
            [{
                'status': 'scheduled',
                'records': test_records_1_replied,
                'fields_values': {
                    'schedule_date': False,
                },
            }],
            act3_1,
        )

        self.assertFalse(captured_triggers.records)  # no trigger should be created

        with freeze_time(date_reference_new), \
             self.mockSMSGateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            self.env['sms.sms'].sudo()._process_queue()

        self.assertMarketAutoTraces(
            [{
                'status': 'processed',
                'records': test_records_1_replied,
                'fields_values': {
                    'schedule_date': date_reference_reply + relativedelta(hours=1),
                },
                'trace_status': 'pending',
            }, {
                'status': 'scheduled',
                'records': test_records_init - test_records_1_replied,
                'fields_values': {
                    'schedule_date': False,
                },
            }],
            act2_1,
        )

        self.assertFalse(captured_triggers.records)  # no trigger should be created

        # ACT2_1 FOLLOWUP: CLICK ON LINKS -> ACT3_1: CONFIRMATION SMS SENT
        # ------------------------------------------------------------

        self._clear_outgoing_sms()
        # TDE CLEANME: improve those tools, but sms gateway resets finding existing
        # sms, which is why we do in two steps
        test_records_1_clicked = test_records_1_replied[0]
        sms_sent = self._find_sms_sent(test_records_1_clicked.customer_id, test_records_1_clicked.phone_sanitized)

        # mock SMS gateway as in the same transaction, next activity is processed
        with freeze_time(date_reference_new), \
             self.mockSMSGateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            self.gateway_sms_sent_click(sms_sent)

        self.assertFalse(captured_triggers.records)  # no trigger should be created

        with freeze_time(date_reference_new), \
             self.mockSMSGateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            self.env['sms.sms'].sudo()._process_queue()

        self.assertFalse(captured_triggers.records)  # no trigger should be created

        # click triggers process_event and automatically launches act3_1 depending on sms_click
        self.assertMarketAutoTraces(
            [{
                'status': 'processed',
                'records': test_records_1_clicked,
                'fields_values': {
                    'schedule_date': date_reference_new,
                },
                # mailing trace
                'trace_content': f'Confirmation for {test_records_1_clicked.name}',
                'trace_status': 'pending',
            }, {
                'status': 'scheduled',
                'records': test_records_1_replied - test_records_1_clicked,
                'fields_values': {
                    'schedule_date': False,
                },
            }],
            act3_1,
        )

        # ACT2_2: PROCESS SERVER ACTION ON NOT-REPLIED (+1D 2H)
        # ------------------------------------------------------------

        date_reference_new = date_reference + relativedelta(days=1, hours=2)
        self._clear_outgoing_sms()
        with freeze_time(date_reference_new), \
             mute_logger('odoo.addons.marketing_automation.models.marketing_activity'), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers:
            campaign.execute_activities()

        self.assertMarketAutoTraces(
            [{
                'status': 'processed',
                'records': test_records_1_ok - test_records_1_replied,
                'fields_values': {
                    'schedule_date': date_reference_new,
                },
            }, {
                'status': 'error',
                'records': (self.test_records_failure_wrong + self.test_records_failure_dupe),  # server action did crash, description is False (see muted logger)
                'fields_values': {
                    'schedule_date': date_reference_new,
                    'state_msg_content': 'Exception in server action',
                },
            }, {
                'status': 'rejected',
                'records': (test_records_1_ko - self.test_records_failure_wrong - self.test_records_failure_dupe),  # no email_from -> rejected due to domain filter
                'fields_values': {
                    'schedule_date': date_reference + relativedelta(days=1),
                },
            }, {
                'status': 'canceled',
                'records': test_records_1_replied,  # replied -> mail_not_open is canceled
                'fields_values': {
                    'schedule_date': date_reference_reply,
                },
            }],
            act2_2,
        )

        # check server action was actually processed
        for record in test_records_1_ko | test_records_1_replied:
            self.assertNotIn('Did not answer, sad campaign is sad', (record.description or ''))
        for record in test_records_1_ok - test_records_1_replied:
            self.assertIn('Did not answer, sad campaign is sad', (record.description or ''))
        self.assertFalse(captured_triggers.records)  # no trigger should be created
