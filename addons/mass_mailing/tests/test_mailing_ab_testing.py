# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import users, tagged
from odoo.tools import mute_logger
from odoo.tests.common import Form
from odoo import fields


@tagged('post_install', '-at_install')
class TestMailingABTestingCommon(MassMailCommon):

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
        self.env.flush_all()
        self.env.invalidate_all()

class TestMailingABTesting(TestMailingABTestingCommon):

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
        self.ab_testing_mailing_ids.invalidate_recordset()

        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 66)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 50)

        with self.mock_mail_gateway():
            self.ab_testing_mailing_2.action_send_winner_mailing()
        self.ab_testing_mailing_ids.invalidate_recordset()
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
        self.ab_testing_mailing_ids.invalidate_recordset()

        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 66)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 50)

        with self.mock_mail_gateway():
            self.env.ref('mass_mailing.ir_cron_mass_mailing_ab_testing').sudo().method_direct_trigger()
        self.ab_testing_mailing_ids.invalidate_recordset()
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
        ab_mailing.invalidate_recordset()

        # Check if the campaign is correctly created and the values set on the mailing are still the same
        self.assertTrue(ab_mailing.campaign_id, "A campaign id is present for the A/B test mailing")
        self.assertEqual(ab_mailing.ab_testing_winner_selection, 'manual', "The selection winner has been propagated correctly")
        self.assertEqual(ab_mailing.ab_testing_schedule_datetime, schedule_datetime, "The schedule date has been propagated correctly")

        # Check that while enabling the A/B testing, if campaign is already set, new one should not be created
        created_mailing_campaign = ab_mailing.campaign_id
        ab_mailing.ab_testing_enabled = False
        ab_mailing.ab_testing_enabled = True
        self.assertEqual(ab_mailing.campaign_id, created_mailing_campaign, "No new campaign should have been created")

        # Check that while enabling the A/B testing, if user manually selects a campaign, it should be saved
        # rather than being replaced with the automatically created one
        ab_mailing.write({'ab_testing_enabled': False, 'campaign_id': False})
        ab_mailing.write({'ab_testing_enabled': True, 'campaign_id': created_mailing_campaign})
        self.assertEqual(ab_mailing.campaign_id, created_mailing_campaign, "No new campaign should have been created")

        ab_mailing_2 = self.env['mailing.mailing'].create({
            'subject': 'A/B Testing V2',
            'contact_list_ids': self.mailing_list.ids,
        })
        ab_mailing_2.invalidate_recordset()

        ab_mailing_2.ab_testing_enabled = True
        # Check if the campaign is correctly created with default values
        self.assertTrue(ab_mailing.campaign_id, "A campaign id is present for the A/B test mailing")
        self.assertTrue(ab_mailing.ab_testing_winner_selection, "The selection winner has been set to default value")
        self.assertTrue(ab_mailing.ab_testing_schedule_datetime, "The schedule date has been set to default value")

    @users('user_marketing')
    def test_mailing_ab_testing_compare(self):
        # compare version feature should returns all mailings of the same
        # campaign having a/b testing enabled.
        compare_version = self.ab_testing_mailing_1.action_compare_versions()
        self.assertEqual(
            self.env['mailing.mailing'].search(compare_version.get('domain')),
            self.ab_testing_mailing_1 + self.ab_testing_mailing_2
        )

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
        self.ab_testing_mailing_ids.invalidate_recordset()

        self.assertEqual(self.ab_testing_mailing_1.opened_ratio, 66)
        self.assertEqual(self.ab_testing_mailing_2.opened_ratio, 50)

        with self.mock_mail_gateway():
            self.ab_testing_mailing_2.action_send_winner_mailing()
        self.ab_testing_mailing_ids.invalidate_recordset()
        winner_mailing = self.ab_testing_campaign.mailing_mail_ids.filtered(lambda mailing: mailing.ab_testing_pc == 100)
        self.assertEqual(winner_mailing.subject, 'A/B Testing V2')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_ab_testing_minimum_participants(self):
        """ Test that it should send minimum one mail(if possible) when ab_testing_pc is too small compared to the amount of targeted records."""
        mailing_list = self._create_mailing_list_of_x_contacts(10)
        ab_testing = self.env['mailing.mailing'].create({
            'subject': 'A/B Testing SMS V1',
            'contact_list_ids': mailing_list.ids,
            'ab_testing_enabled': True,
            'ab_testing_pc': 2,
            'ab_testing_schedule_datetime': datetime.now(),
            'mailing_type': 'mail',
            'campaign_id': self.ab_testing_campaign.id,
        })
        with self.mock_mail_gateway():
            ab_testing.action_send_mail()
        self.assertEqual(ab_testing.state, 'done')
        self.assertEqual(len(self._mails), 1)

    def test_mailing_ab_testing_duplicate_date(self):
        """ Test that "Send final on" date value should be copied in new mass_mailing """
        ab_testing_mail_1 = Form(self.ab_testing_mailing_1)
        ab_testing_mail_1.ab_testing_schedule_datetime = datetime.now() + timedelta(days=10)
        action = ab_testing_mail_1.save().action_duplicate()
        ab_testing_mailing_2 = self.env[action['res_model']].browse(action['res_id'])
        self.assertEqual(fields.Datetime.to_string(ab_testing_mailing_2.ab_testing_schedule_datetime), ab_testing_mail_1.ab_testing_schedule_datetime)
