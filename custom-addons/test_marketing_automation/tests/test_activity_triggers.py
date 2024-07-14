# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time

from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.fields import Datetime
from odoo.tests import tagged, users


class ActivityTriggersCase(TestMACommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date_reference = Datetime.from_string('2023-11-08 09:00:00')

        # --------------------------------------------------
        # TEST RECORDS, using marketing.test.sms (customers)
        #
        # 2 times
        # - 3 records with partners
        # - 1 records wo partner, but email/mobile
        # - 1 record wo partner/email/mobile
        # --------------------------------------------------
        cls.test_records_base = cls._create_marketauto_records(model='marketing.test.sms', count=2)
        cls.test_records = cls.test_records_base
        cls.test_records_ko = cls.test_records_base[4] + cls.test_records_base[9]
        cls.test_records_ok = cls.test_records - cls.test_records_ko

        cls.campaign = cls.env['marketing.campaign'].create({
            'domain': [('id', 'in', cls.test_records.ids)],
            'model_id': cls.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'Test Campaign',
        })

        cls.test_mailing_mail = cls._create_mailing(
            'marketing.test.sms',
            email_from=cls.user_marketing_automation.email_formatted,
            keep_archives=True,
            mailing_type='mail',
            user_id=cls.user_marketing_automation.id,
        )
        cls.test_mailing_sms = cls._create_mailing(
            'marketing.test.sms',
            mailing_type='sms',
            body_plaintext='Test SMS',
            user_id=cls.user_marketing_automation.id,
        )

        cls.test_sa_descr = cls.env['ir.actions.server'].create([
            {
                'code': f"""
for record in records:
    record.write({{'description': (record.description or '') + ' - {description}'}})""",
                'model_id': cls.env['ir.model']._get_id('marketing.test.sms'),
                'name': f'Update {description}',
                'state': 'code',
            } for description in [
                'mail_open', 'mail_not_open',
                'mail_reply', 'mail_not_reply',
                'mail_click', 'mail_not_click',
                'mail_bounce',
            ]
        ])
        (cls.test_sa_descr_mail_open, cls.test_sa_descr_mail_not_open,
            cls.test_sa_descr_mail_reply, cls.test_sa_descr_mail_not_reply,
            cls.test_sa_descr_mail_click, cls.test_sa_descr_mail_not_click,
            cls.test_sa_descr_mail_bounce) = cls.test_sa_descr
        cls.test_sa_unlink = cls.env['ir.actions.server'].create({
            'code': "records.unlink()",
            'model_id': cls.env['ir.model']._get_id('marketing.test.sms'),
            'name': 'Unlink',
            'state': 'code',
        })

        cls.env.flush_all()

    def _launch_campaign(self, campaign, date_reference=None):
        campaign.action_start_campaign()
        with freeze_time(date_reference or self.date_reference):
            campaign.sync_participants()


@tagged('marketing_automation', 'marketing_activity')
class TestActivityTriggers(ActivityTriggersCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.activity_mailing_mail = cls._create_activity(
            cls.campaign,
            create_date=cls.date_reference,
            mailing=cls.test_mailing_mail,
            interval_number=1, interval_type='hours',
            trigger_type='begin',
        )
        cls.activity_sa_notopen = cls._create_activity(
            cls.campaign,
            action=cls.test_sa_descr_mail_not_open,
            parent_id=cls.activity_mailing_mail.id,
            interval_number=1, interval_type='days',
            trigger_type='mail_not_open',
        )
        cls.activity_sa_open = cls._create_activity(
            cls.campaign,
            action=cls.test_sa_descr_mail_open,
            parent_id=cls.activity_mailing_mail.id,
            interval_number=0,
            trigger_type='mail_open',
        )

        cls.activity_mailing_sms = cls._create_activity(
            cls.campaign,
            create_date=cls.date_reference,
            mailing=cls.test_mailing_sms,
            interval_number=1, interval_type='hours',
            trigger_type='begin',
        )
        cls.activity_sms_not_click = cls._create_activity(
            cls.campaign,
            action=cls.test_sa_descr_mail_open,
            parent_id=cls.activity_mailing_sms.id,
            interval_number=0,
            trigger_type='sms_not_click',
        )

    @users('user_marketing_automation')
    def test_mail_open(self):
        """ Test mail triggers (open / not_open) """
        campaign = self.campaign.with_env(self.env)
        activity_mailing = self.activity_mailing_mail.with_env(self.env)
        activity_sa_notopen = self.activity_sa_notopen.with_env(self.env)
        activity_sa_open = self.activity_sa_open.with_env(self.env)
        test_records = self.test_records.with_env(self.env)
        test_records_ok = self.test_records_ok.with_env(self.env)
        test_records_ko = self.test_records_ko.with_env(self.env)

        self._launch_campaign(campaign)
        self.assertMarketAutoTraces(
            [{
                'records': test_records,
                'status': 'scheduled',
                'fields_values': {
                    'schedule_date': self.date_reference + timedelta(hours=1),
                }
            }],
            activity_mailing,
        )
        self.assertActivityWoTrace(activity_sa_open + activity_sa_notopen)

        # First traces are processed, emails are sent (or failed)
        date_send = self.date_reference + timedelta(hours=1)  # ok for send mailing
        date_opened = date_send + timedelta(hours=2)  # simulating opened
        date_noreply = date_send + timedelta(days=1)  # 1 day delay before triggering 'did not reply'
        with freeze_time(date_send), self.mock_mail_gateway():
            campaign.execute_activities()

        self.assertMarketAutoTraces(
            [{
                'records': test_records_ok,
                'status': 'processed',
                'fields_values': {
                    'schedule_date': self.date_reference + timedelta(hours=1),
                },
                'trace_status': 'sent',
            }, {
                'records': test_records_ko,
                'status': 'canceled',
                'fields_values': {
                    'schedule_date': self.date_reference + timedelta(hours=1),
                    'state_msg': 'Email canceled',
                },
                'trace_failure_type': 'mail_email_missing',
                'trace_status': 'cancel',
            }],
            activity_mailing,
        )
        for sub_activity, schedule_date in [
            (activity_sa_open, False),
            (activity_sa_notopen, date_noreply),
        ]:
            self.assertMarketAutoTraces(
                [{
                    'records': test_records,
                    'status': 'scheduled',
                    'fields_values': {
                        'schedule_date': schedule_date,
                    }
                }],
                sub_activity,
            )

        # Simulate open
        # - open traces should be processed, schedule date updated
        # - not_open traces should be canceled
        to_open = test_records_ok[:5]
        with freeze_time(date_opened):
            for record in to_open:
                self.gateway_mail_open(activity_mailing.mass_mailing_id, record)
        self.assertMarketAutoTraces(
            [{
                'records': to_open,
                'status': 'processed',
                'fields_values': {
                    'schedule_date': date_opened,
                    'state_msg': False,
                }
            }, {
                'records': test_records - to_open,
                'status': 'scheduled',
                'fields_values': {
                    'schedule_date': False,
                }
            }],
            activity_sa_open,
        )
        self.assertMarketAutoTraces(
            [{
                'records': to_open,
                'status': 'canceled',
                'fields_values': {
                    'schedule_date': date_opened,
                    'state_msg': 'Parent activity mail opened',
                }
            }, {
                'records': test_records - to_open,
                'status': 'scheduled',
                'fields_values': {
                    'schedule_date': date_noreply,
                }
            }],
            activity_sa_notopen,
        )

    @users('user_marketing_automation')
    def test_triggers(self):
        self._launch_campaign(self.campaign)
        date_send = self.date_reference + timedelta(hours=1)
        date_not_clicked = date_send + timedelta(hours=0)
        date_not_open = date_send + timedelta(days=1)

        with freeze_time(date_send), self.mock_mail_gateway():
            self.campaign.execute_activities()

        for sub_activity, schedule_date in [
            (self.activity_sms_not_click, date_not_clicked),
            (self.activity_sa_notopen, date_not_open),
        ]:
            self.assertMarketAutoTraces(
                [{
                    'records': self.test_records,
                    'status': 'scheduled',
                    'fields_values': {
                        'schedule_date': schedule_date,
                    }
                }],
                sub_activity,
            )
