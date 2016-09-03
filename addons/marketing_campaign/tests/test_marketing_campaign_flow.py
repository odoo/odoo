# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestMarketingCampaignFlow(common.TransactionCase):

    def test_00_marketing_campaign_flow(self):

        Workitem = self.env['marketing.campaign.workitem']

        # In order to test process of compaign, I start compaign.
        partner_channel = self.env.ref('marketing_campaign.marketing_campaign_openerppartnerchannel')
        partner_channel.state_running_set()

        # I check the campaign on Running mode after started.
        self.assertEqual(partner_channel.state, 'running', 'The campaign should be on Running mode after having started.')

        # I start this segment after assinged campaign.
        segment0 = self.env.ref('marketing_campaign.marketing_campaign_segment0')
        segment0.state_running_set()

        # I check the segment on Running mode after started.
        self.assertEqual(segment0.state, 'running', 'The segment should be on Running mode after having started.')

        # I synchronized segment manually to see all step of activity and process covered on this campaign.
        self.assertTrue(segment0.date_next_sync, 'Next Synchronization date is not calculated.')
        segment0.process_segment()

        # I cancel Marketing Workitems.
        workitems = Workitem.search([
            ('segment_id', '=', segment0.id),
            ('campaign_id', '=', partner_channel.id)
        ])
        workitems.button_cancel()
        self.assertTrue(workitems[0].state in ('cancelled', 'done'), 'Marketing Workitem shoud be in cancel state.')

        # I set Marketing Workitems in draft state.
        workitems.button_draft()
        self.assertTrue(workitems[0].state in ('todo', 'done'), 'Marketing Workitem shoud be in draft state.')

        # I process follow-up of first activity.
        activity0_id = self.ref('marketing_campaign.marketing_campaign_activity_0')
        workitems = Workitem.search([
            ('segment_id', '=', segment0.id),
            ('campaign_id', '=', partner_channel.id),
            ('activity_id', '=', activity0_id)
        ])
        self.assertTrue(workitems, 'Follow-up item is not created for first activity.')
        self.assertTrue(workitems[0].res_name, 'Resource Name is not defined.')
        workitems.process()
        self.assertEqual(workitems[0].state, 'done', "Follow-up item should be closed after process.")

        # I check follow-up detail of second activity after process of first activity.
        activity1_id = self.ref('marketing_campaign.marketing_campaign_activity_1')
        workitems = Workitem.search([
            ('segment_id', '=', segment0.id),
            ('campaign_id', '=', partner_channel.id),
            ('activity_id', '=', activity1_id)
        ])
        self.assertTrue(workitems, 'Follow-up item is not created for second activity.')

        # Now I increase credit limit of customer
        self.env.ref("base.res_partner_2").write({'credit_limit': 41000})

        # I process follow-up of second activity after set draft.
        workitems.button_draft()
        workitems.process()
        self.assertEqual(workitems[0].state, 'done', "Follow-up item should be closed after process.")

        # I check follow-up detail of third activity after process of second activity.
        activity2_id = self.ref('marketing_campaign.marketing_campaign_activity_2')
        workitems = Workitem.search([
            ('segment_id', '=', segment0.id),
            ('campaign_id', '=', partner_channel.id),
            ('activity_id', '=', activity2_id)
        ])
        self.assertTrue(workitems, 'Follow-up item is not created for third activity.')

        # Now I increase credit limit of customer
        self.env.ref("base.res_partner_2").write({'credit_limit': 151000})

        # I process follow-up of third activity after set draft.
        workitems.button_draft()
        workitems.process()
        self.assertEqual(workitems[0].state, 'done', "Follow-up item should be closed after process.")

        # I print workitem report
        workitems.preview()

        # I cancel segmentation because of some activity.
        segment0.state_cancel_set()

        # I check the segmentation is canceled.
        self.assertEqual(segment0.state, 'cancelled', 'Segment should be in cancelled state.')

        # I reopen the segmentation.
        segment0.state_draft_set()
        segment0.state_running_set()

        # I check the segment on Running mode after started.
        self.assertEqual(segment0.state, 'running', 'Segment should be in running state.')

        # I close segmentation After completion of all activity.
        segment0.state_done_set()

        # I check the segmentation is done.
        self.assertEqual(segment0.state, 'done', 'Segment should be in done state.')

        # I close this campaing.
        partner_channel.state_done_set()

        # I check the campaing is done.
        self.assertEqual(partner_channel.state, 'done', 'Campaign should be in done state.')
