from dateutil.relativedelta import relativedelta

from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.fields import Datetime
from odoo.tests import tagged, users


@tagged('post_install', '-at_install', 'marketing_automation', 'twilio')
class TestMarketingAutomationSms(TestMACommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date_reference = Datetime.from_string('2025-08-22 11:15:30')
        cls.env['res.lang']._activate_lang('fr_FR')
        cls._setup_sms_twilio(cls.user_marketing_automation.company_id)

        # --------------------------------------------------
        # TEST RECORDS, using marketing.test.sms (customers)
        #
        # 2 times
        # - 3 records with partners
        # - 1 records wo partner, but email/mobile
        # - 1 record wo partner/email/mobile
        # 1 wrong email
        # 1 duplicate
        # --------------------------------------------------
        cls.test_records_base = cls._create_marketauto_records(model='marketing.test.sms', count=2)
        cls.test_records_failure = cls.env['marketing.test.sms'].create([
            {
                'email_from': 'wrong',
                'name': 'Wrong',
                'phone': '87645',
            }, {
                'email_from': cls.test_records_base[1].email_from,
                'mobile': cls.test_records_base[1].mobile,
                'phone': cls.test_records_base[1].phone,
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
        # ACT1           SMS mailing
        #   ACT1.1       -> bounce -> archive record
        # --------------------------------------------------

        cls.campaign = cls.env['marketing.campaign'].with_user(cls.user_marketing_automation).create({
            'model_id': cls.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'Test SMS Campaign',
        })
        # first activity: send a SMS mailing
        cls.act1_sms_mailing = cls._create_mailing(
            'marketing.test.sms',
            mailing_type='sms',
            body_plaintext='SMS for {{ object.name }}: mega promo on https://test.example.com',
            sms_allow_unsubscribe=True,
        ).with_user(cls.user_marketing_automation)
        cls.act1 = cls._create_activity(
            cls.campaign,
            mailing=cls.act1_sms_mailing,
            trigger_type='begin',
            interval_number=1,
            interval_type='hours',
        ).with_user(cls.user_marketing_automation)
        # server action: archive record
        cls.act1_1_sact = cls.env['ir.actions.server'].create({
            'code': 'records.action_archive()',
            'model_id': cls.env['ir.model']._get('marketing.test.sms').id,
            'name': 'Archive records',
            'state': 'code',
        })
        cls.act1_1 = cls._create_activity(
            cls.campaign,
            action=cls.act1_1_sact,
            parent_id=cls.act1.id,
            trigger_type='sms_bounce',
            interval_number=0,
        ).with_user(cls.user_marketing_automation)

        cls.env.flush_all()

    def test_assert_initial_values(self):
        """ Test initial values to have a common ground for other tests """
        # ensure initial data
        self.assertEqual(len(self.test_records), 12)
        self.assertEqual(self.campaign.state, 'draft')

    @users('user_marketing_automation')
    def test_marketing_automation_flow(self):
        """ Test a marketing automation flow involving several steps. """
        # init test variables to ease code reading
        data_reference_start = self.date_reference + relativedelta(hours=1)
        test_records = self.test_records.with_user(self.env.user)

        # update campaign
        act1 = self.act1.with_user(self.env.user)
        _act1_1 = self.act1_1.with_user(self.env.user)
        campaign = self.campaign.with_user(self.env.user)

        # CAMPAIGN START
        # ------------------------------------------------------------

        # User starts and syncs its campaign
        with self.mock_datetime_and_now(self.date_reference):
            campaign.action_start_campaign()
            campaign.sync_participants()

        # All records not containing Test_00 should be added as participants
        self.assertEqual(campaign.running_participant_count, len(test_records))
        self.assertEqual(
            set(campaign.participant_ids.mapped('res_id')),
            set(test_records.ids)
        )
        self.assertEqual(
            set(campaign.participant_ids.mapped('state')),
            {'running'}
        )

        # Beginning activity should contain a scheduled trace for each participant
        self.assertMarketAutoTraces(
            [{
                'fields_values': {
                    'schedule_date': data_reference_start,
                },
                'participants': campaign.participant_ids,
                'records': test_records,
                'status': 'scheduled',
            }],
            act1,
        )

        # ACT1: LAUNCH SMS MAILING
        # ------------------------------------------------------------
        test_records_1_ko = test_records.filtered(
            lambda r: not r.phone or r.phone == "87645"
        ) + self.test_records_failure_dupe
        test_records_1_ok = test_records.filtered(lambda r: r not in test_records_1_ko)

        with self.mock_datetime_and_now(data_reference_start), \
             self.mockSMSGateway(), self.mock_sms_twilio_send():
            campaign.execute_activities()
            self.env['sms.sms'].sudo()._process_queue()
        # SMS are sent one call at a time
        self.assertEqual(self._sms_twilio_send_mock.call_count, 8)

        # simulate ack reception from twilio
        sms_batch = self._new_sms.filtered(
            lambda sms: sms.mailing_trace_ids.res_id in test_records_1_ok.ids,
        )
        self.simulate_sms_twilio_status(sms_batch, self.user_marketing_automation.company_id)

        self.assertMarketAutoTraces(
            [{
                'fields_values': {
                    'schedule_date': data_reference_start,
                    'state_msg': False,
                },
                'records': test_records_1_ok,
                'status': 'processed',
                'trace_status': 'sent',
            }, {
                # wrong phone -> trace set as ignored
                'fields_values': {
                    'schedule_date': data_reference_start,
                    'state_msg': 'SMS cancelled',
                },
                'records': self.test_records_failure_wrong,
                'status': 'canceled',
                'trace_failure_type': 'sms_number_format',
                'trace_sms_number': '87645',
                'trace_status': 'cancel',
            }, {
                # wrong phone -> trace set as ignored
                'fields_values': {
                    'schedule_date': data_reference_start,
                    'state_msg': 'SMS cancelled',
                },
                'records': self.test_records_failure_dupe,
                'status': 'canceled',
                'trace_failure_type': 'sms_duplicate',
                'trace_status': 'cancel',
            }, {
                # no phone -> trace set as ignored
                'check_sms': False,  # cannot differentiate 2 void sms -> no need to check anyway
                'fields_values': {
                    'schedule_date': data_reference_start,
                    'state_msg': 'SMS cancelled',
                },
                'records': (test_records_1_ko - self.test_records_failure_wrong - self.test_records_failure_dupe),
                'status': 'canceled',
                # TDE checkme
                'trace_failure_type': 'mail_email_missing',
                'trace_status': 'cancel',
            }],
            act1,
        )
