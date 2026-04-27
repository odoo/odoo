# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.tests import tagged, users
from odoo.tests import Form


@tagged("marketing_automation", "utm")
class TestMarketingCampaign(TestMACommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date_reference = datetime(2025, 6, 23, 14, 0, 0)

        with cls.mock_datetime_and_now(cls, cls.date_reference):
            # create a marketing campaign with a parent activity with one child activity
            cls.test_campaign = cls.env['marketing.campaign'].with_user(cls.user_marketing_automation).create({
                'domain': [('name', 'like', 'MATest')],
                'model_id': cls.env['ir.model']._get_id('marketing.test.sms'),
                'name': 'New Test Campaign',
            })
            cls.activity1 = cls._create_activity_mail(
                cls.test_campaign,
                user=cls.user_marketing_automation,
                act_values={
                    'trigger_type': 'begin',
                    'interval_number': 1, 'interval_type': 'hours',
                },
                mailing_values={
                    'body_html': """<div><p>Hello {{ object.name }}</p>
<p>click here <a id="url0" href="https://www.example.com/test/bar?baz=qux">LINK</a></p>
</div>""",
                },
            )
            cls.activity1_1 = cls._create_activity_mail(
                cls.test_campaign,
                user=cls.user_marketing_automation,
                act_values={
                    'trigger_type': 'activity',
                    'interval_number': 1, 'interval_type': 'hours',
                    'parent_id': cls.activity1.id,
                },
            )

    @users('user_marketing_automation')
    def test_campaign_tests_mailing_trace_marketing_trace_relation(self):
        """
        Tests that marketing traces and mailing traces for activities and participants
        correctly get linked together
        """
        campaign = self.test_campaign.with_user(self.env.user)
        activity1 = self.activity1.with_user(self.env.user)
        TestModel = self.env['marketing.campaign.test'].with_context(active_model='marketing.campaign.test', default_campaign_id=campaign.id)
        # fetch a contact for tests to work over
        test_record = self.env['marketing.test.sms'].create({
            'email_from': 'test_contact@example.com',
            'name': 'MATest',
        })
        # launch a test
        test1 = Form(TestModel)
        test1.resource_ref = test_record
        test1.save().action_launch_test()
        participant1 = self.env['marketing.participant'].search([
            ('campaign_id', '=', campaign.id),
            ('res_id', '=', test_record.id),
            ('model_name', '=', test_record._name),
        ])
        participant1.ensure_one()
        p1_initial_trace = participant1.trace_ids
        self.assertEqual(len(p1_initial_trace), 1, 'Should have prepared trace for begin activity only')
        # launch first parent activity, under test context
        with self.mock_datetime_and_now(self.date_reference + timedelta(hours=1)), \
             self.mock_mail_gateway():
            p1_initial_trace.with_context(active_model='marketing.campaign.test').action_execute()
        self.assertEqual(p1_initial_trace.state, 'processed', 'Should have been processed')
        # check link tracker
        self.assertNotIn('https://www.example.com/test/bar?baz=qux', self._new_mails[0].body)
        self.assertLinkShortenedHtml(
            self._new_mails[0].body,
            ('url0', 'https://www.example.com/test/bar?baz=qux', True),
            {'baz': 'qux', 'utm_campaign': campaign.name, 'utm_medium': 'Email', 'utm_source': activity1.name},
        )
        # don't launch first child activity, but check that it exists
        self.assertEqual(len(participant1.trace_ids), 2, 'Should have prepared planned child activity')
        p1_child = participant1.trace_ids.filtered(lambda trace: trace.parent_id == p1_initial_trace)
        self.assertTrue(p1_child)
        self.assertEqual(p1_child.state, 'scheduled')

        # launch another test
        test2 = Form(TestModel)
        test2.resource_ref = test_record
        test2.save().action_launch_test()
        participant2 = self.env['marketing.participant'].search([
            ('id', '!=', participant1.id),
            ('campaign_id', '=', campaign.id),
            ('res_id', '=', test_record.id),
            ('model_name', '=', test_record._name),
        ])
        participant2.ensure_one()
        p2_initial_trace = participant2.trace_ids
        self.assertEqual(len(p2_initial_trace), 1, 'Should have prepared trace for begin activity only')
        # launch second parent activity, under test context
        with self.mock_datetime_and_now(self.date_reference + timedelta(hours=1)), \
             self.mock_mail_gateway():
            p2_initial_trace.with_context(active_model='marketing.campaign.test').action_execute()
        self.assertEqual(p2_initial_trace.state, 'processed', 'Should have been processed')
        # check link tracker
        self.assertNotIn('https://www.example.com/test/bar?baz=qux', self._new_mails[0].body)
        self.assertLinkShortenedHtml(
            self._new_mails[0].body,
            ('url0', 'https://www.example.com/test/bar?baz=qux', True),
            {'baz': 'qux', 'utm_campaign': campaign.name, 'utm_medium': 'Email', 'utm_source': activity1.name},
        )
        # don't launch first child activity, but check that it exists
        self.assertEqual(len(participant2.trace_ids), 2, 'Should have prepared planned child activity')
        p2_child = participant2.trace_ids.filtered(lambda trace: trace.parent_id == p2_initial_trace)
        self.assertTrue(p2_child)
        self.assertEqual(p2_child.state, 'scheduled')

        # check participant status
        self.assertEqual(
            participant1.state, 'completed',
            'Relaunching test on same record should close the old participant')
        self.assertEqual(participant2.state, 'running')

        # launch second child activity
        participant2.trace_ids.filtered(lambda trace: trace.parent_id).action_execute()

        # check traces
        # assert that the parents and the second child have one (1) mailing trace
        self.assertEqual(len(p1_initial_trace.mailing_trace_ids), 1)
        self.assertEqual(len(p2_initial_trace.mailing_trace_ids), 1)
        self.assertEqual(len(p2_child.mailing_trace_ids), 1)
        # assert that the first child has no mailing traces
        self.assertEqual(len(p1_child.mailing_trace_ids), 0)

        # check participant status
        self.assertEqual(participant1.state, 'completed')
        self.assertEqual(participant2.state, 'completed', 'All activities done')
