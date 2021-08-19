# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import users, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestMailingABTesting(MassMailCommon):
    def setUp(self):
        super().setUp()
        self.mailing_list = self._create_mailing_list_of_x_contacts(150)
        self.ab_testing_mailing_1 = self.env['mailing.mailing'].create({
            'subject': 'A/B Testing V1',
            'contact_list_ids': self.mailing_list.ids,
            'ab_testing_enabled': True,
            'ab_testing_pc': 10,
            'ab_testing_schedule_datetime': datetime.now(),
        })
        self.ab_testing_mailing_2 = self.ab_testing_mailing_1.copy({
            'subject': 'A/B Testing V2',
            'ab_testing_pc': 20,
        })
        self.ab_testing_campaign = self.ab_testing_mailing_1.campaign_id
        self.ab_testing_mailing_ids = self.ab_testing_mailing_1 + self.ab_testing_mailing_2
        self.ab_testing_mailing_ids.invalidate_cache()

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_ab_testing_auto_flow(self):
        with self.mock_mail_gateway():
            self.ab_testing_mailing_ids.action_send_mail()
        self.assertEqual(self.ab_testing_mailing_1.state, 'done')
        self.assertEqual(self.ab_testing_mailing_2.state, 'done')
        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 0)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 0)

        total_trace_ids = self.ab_testing_mailing_ids.mailing_trace_ids
        unique_recipients_used = set(map(lambda mail: mail.res_id, total_trace_ids.mail_mail_id))
        self.assertEqual(len(self.ab_testing_mailing_1.mailing_trace_ids), 15)
        self.assertEqual(len(self.ab_testing_mailing_2.mailing_trace_ids), 30)
        self.assertEqual(len(unique_recipients_used), 45)

        self.ab_testing_mailing_1.mailing_trace_ids[:10].set_opened()
        self.ab_testing_mailing_2.mailing_trace_ids[:15].set_opened()
        self.ab_testing_mailing_ids.invalidate_cache()

        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 66)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 50)

        with self.mock_mail_gateway():
            self.ab_testing_mailing_2.action_send_winner_mailing()
        self.ab_testing_mailing_ids.invalidate_cache()
        winner_mailing = self.ab_testing_campaign.mailing_mail_ids.filtered(lambda mailing: mailing.ab_testing_pc == 100)
        self.assertEqual(winner_mailing.subject, 'A/B Testing V1')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_ab_testing_auto_flow_cron(self):
        self.ab_testing_mailing_1.write({
            'ab_testing_schedule_datetime': datetime.now() + timedelta(days=-1),
        })
        with self.mock_mail_gateway():
            self.ab_testing_mailing_ids.action_send_mail()
        self.assertEqual(self.ab_testing_mailing_1.state, 'done')
        self.assertEqual(self.ab_testing_mailing_2.state, 'done')
        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 0)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 0)

        total_trace_ids = self.ab_testing_mailing_ids.mailing_trace_ids
        unique_recipients_used = set(map(lambda mail: mail.res_id, total_trace_ids.mail_mail_id))
        self.assertEqual(len(self.ab_testing_mailing_1.mailing_trace_ids), 15)
        self.assertEqual(len(self.ab_testing_mailing_2.mailing_trace_ids), 30)
        self.assertEqual(len(unique_recipients_used), 45)

        self.ab_testing_mailing_1.mailing_trace_ids[:10].set_opened()
        self.ab_testing_mailing_2.mailing_trace_ids[:15].set_opened()
        self.ab_testing_mailing_ids.invalidate_cache()

        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 66)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 50)

        with self.mock_mail_gateway():
            self.env.ref('mass_mailing.ir_cron_mass_mailing_ab_testing').sudo().method_direct_trigger()
        self.ab_testing_mailing_ids.invalidate_cache()
        winner_mailing = self.ab_testing_campaign.mailing_mail_ids.filtered(lambda mailing: mailing.ab_testing_pc == 100)
        self.assertEqual(winner_mailing.subject, 'A/B Testing V1')

    @users('user_marketing')
    def test_mailing_ab_testing_campaign(self):
        schedule_datetime = datetime.now() + timedelta(days=30)
        ab_mailing = self.env['mailing.mailing'].create({
            'subject': 'A/B Testing V1',
            'contact_list_ids': self.mailing_list.ids,
            'ab_testing_enabled': True,
            'ab_testing_winner_selection': 'manual',
            'ab_testing_schedule_datetime': schedule_datetime,
        })
        ab_mailing.invalidate_cache()

        # Check if the campaign is correclty created and the values set on the mailing are still the same
        self.assertTrue(ab_mailing.campaign_id, "A campaign id is present for the A/B test mailing")
        self.assertEqual(ab_mailing.ab_testing_winner_selection, 'manual', "The selection winner has been propagated correctly")
        self.assertEqual(ab_mailing.ab_testing_schedule_datetime, schedule_datetime, "The schedule date has been propagated correctly")

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_ab_testing_manual_flow(self):
        self.ab_testing_mailing_1.write({
            'ab_testing_winner_selection': 'manual',
        })
        with self.mock_mail_gateway():
            self.ab_testing_mailing_ids.action_send_mail()
        self.assertEqual(self.ab_testing_mailing_1.state, 'done')
        self.assertEqual(self.ab_testing_mailing_2.state, 'done')
        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 0)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 0)

        total_trace_ids = self.ab_testing_mailing_ids.mailing_trace_ids
        unique_recipients_used = set(map(lambda mail: mail.res_id, total_trace_ids.mail_mail_id))
        self.assertEqual(len(self.ab_testing_mailing_1.mailing_trace_ids), 15)
        self.assertEqual(len(self.ab_testing_mailing_2.mailing_trace_ids), 30)
        self.assertEqual(len(unique_recipients_used), 45)

        self.ab_testing_mailing_1.mailing_trace_ids[:10].set_opened()
        self.ab_testing_mailing_2.mailing_trace_ids[:15].set_opened()
        self.ab_testing_mailing_ids.invalidate_cache()

        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 66)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 50)

        with self.mock_mail_gateway():
            self.ab_testing_mailing_2.action_send_winner_mailing()
        self.ab_testing_mailing_ids.invalidate_cache()
        winner_mailing = self.ab_testing_campaign.mailing_mail_ids.filtered(lambda mailing: mailing.ab_testing_pc == 100)
        self.assertEqual(winner_mailing.subject, 'A/B Testing V2')
