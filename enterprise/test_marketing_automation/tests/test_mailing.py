# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.fields import Datetime
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'marketing_automation', 'mass_mailing')
class TestMassMailing(CronMixinCase, TestMACommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailing, cls).setUpClass()

        cls.date_reference = Datetime.from_string('2023-11-08 08:00:00')
        cls.test_records = cls.env['res.partner'].create([{
            'name': 'test1',
            'email': 'test1@test.com',
        }, {
            'name': 'test1',  # complete duplicate, both name and email for dupe check
            'email': 'test1@test.com',
        }, {
            'name': 'test2',
            'email': 'test2@test.com',
        }])

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.mass_mailing.models.mailing')
    def test_mailing_duplicate_is_test(self):
        """ Check that only non-tests records can be considered as duplicates"""
        test_records = self.test_records.with_env(self.env)
        campaign = self.env['marketing.campaign'].create({
            'domain': [('id', 'in', test_records.ids)],
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'Great Campaign',
        })
        activity = self._create_activity_mail(campaign)

        # test campaign flow: we want to make sure that when creating multiple test campaigns with the same customer
        # the customer will still receive multiple mails (not considered as duplicate)
        test_result = self.env['marketing.campaign.test'].create({
            'campaign_id': campaign.id,
            'res_id': test_records[0].id,
        }).action_launch_test()
        new_participant_1 = self.env['marketing.participant'].browse(test_result['res_id'])
        self.assertTrue(new_participant_1.is_test)

        trace_test_1 = self.env['marketing.trace'].search([('participant_id', '=', new_participant_1.id)])
        trace_test_1.flush_recordset()
        with self.mock_datetime_and_now(self.date_reference), self.mock_mail_gateway(mail_unlink_sent=False):
            trace_test_1.action_execute()
        self.assertEqual(len(self._mails), 1)

        test_result = self.env['marketing.campaign.test'].create({
            'campaign_id': campaign.id,
            'res_id': test_records[0].id,
        }).action_launch_test()
        new_participant_2 = self.env['marketing.participant'].browse(test_result['res_id'])
        self.assertTrue(new_participant_2.is_test)
        self.assertNotEqual(new_participant_1, new_participant_2)

        trace_test_2 = self.env['marketing.trace'].search([('participant_id', '=', new_participant_2.id)])
        trace_test_2.flush_recordset()
        with self.mock_datetime_and_now(self.date_reference), self.mock_mail_gateway(mail_unlink_sent=False):
            trace_test_2.action_execute()
        self.assertEqual(len(self._mails), 1, 'test1 should have received an email')

        # normal campaign flow
        self._launch_campaign(campaign, date_reference=self.date_reference)

        self.assertEqual(len(activity.trace_ids), 4)
        self.assertEqual(
            activity.trace_ids.mapped('participant_id'),
            campaign.participant_ids,
        )
        with self.mock_datetime_and_now(self.date_reference), self.mock_mail_gateway(mail_unlink_sent=False):
            activity.execute_on_traces(activity.trace_ids)
        self.assertEqual(len(self._mails), 2, 'Should have sent 2 emails.')
