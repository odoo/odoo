# -*- coding: utf-8 -*-

from odoo.tests import common


class TestMarketingCampaign(common.TransactionCase):

    def test_00_marketing_campaign_tests(self):

        # In order to test process of compaign, I start compaign.
        partnerchannel = self.env.ref(
            'marketing_campaign.marketing_campaign_openerppartnerchannel')
        partnerchannel.signal_workflow('state_running_set')

        # I check the campaign on Running mode after started.
        self.assertEqual(partnerchannel.state, 'running', 'the campaign should be on Running mode after started.')

        # I start this segment after assinged campaign.
        segment0 = self.env.ref(
            'marketing_campaign.marketing_campaign_segment0')
        segment0.signal_workflow('state_running_set')

        # I check the segment on Running mode after started.
        self.assertEqual(segment0.state, 'running', 'the segment should be on Running mode after started.')

        # I synchronized segment manually to see all step of activity and
        # process covered on this campaign.
        self.assertTrue((segment0.date_next_sync), 'Next Synchronization date is not calculated.')
        segment0.synchroniz()

        # I cancel Marketing Workitems.
        Workitem = self.env['marketing.campaign.workitem']
        workitems_01 = Workitem.search(
            [('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id)], limit=1)
        workitems_01.button_cancel()
        self.assertTrue((workitems_01.state == 'cancelled' or workitems_01.state == 'done'), 'Marketing Workitem shoud be in cancel state.')

        # I set Marketing Workitems in draft state.
        workitems_02 = Workitem.search(
            [('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id)], limit=1)
        workitems_02.button_draft()
        self.assertTrue((workitems_02.state == 'todo' or workitems_02.state == 'done'), 'Marketing Workitem shoud be in draft state.')

        # I process follow-up of first activity.
        workitems_03 = Workitem.search([('segment_id', '=', segment0.id),
                                        ('campaign_id', '=', partnerchannel.id), ('activity_id', '=', segment0.id)], limit=1)
        self.assertTrue((workitems_03.ids), 'Follow-up item is not created for first activity.')
        self.assertTrue((workitems_03.res_name), 'Resource Name is not defined.')
        workitems_03.process()
        self.assertTrue((workitems_03.state == "done"), "Follow-up item should be closed after process.")

        # I check follow-up detail of second activity after process of first
        # activity.
        activity1 = self.ref(
            'marketing_campaign.marketing_campaign_activity_1')
        workitems_04 = Workitem.search([('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id), (
            'activity_id', '=', activity1)], limit=1)

        self.assertTrue((workitems_04.ids), 'Follow - up item is not created for second activity.')

        # Now I increase credit limit of customer
        self.env.ref('base.res_partner_2').write({'credit_limit': 41000})

        # I process follow-up of second activity after set draft.
        workitems_05 = Workitem.search([('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id), (
            'activity_id', '=', activity1)], limit=1)
        workitems_05.button_draft()
        workitems_05.process()
        self.assertTrue((workitems_05.state == "done"), "Follow-up item should be closed after process.")

        # I check follow-up detail of third activity after process of second
        # activity.
        activity2 = self.ref(
            'marketing_campaign.marketing_campaign_activity_2')
        workitems_06 = Workitem.search([('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id), (
            'activity_id', '=', activity2)])
        self.assertTrue((workitems_06.ids), 'Follow-up item is not created for third activity.')
        # Now I increase credit limit of customer
        self.env.ref('base.res_partner_2').write({'credit_limit': 151000})

        # I process follow-up of third activity after set draft.
        workitems = Workitem.search([('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id), ('activity_id', '=', activity2)], limit=1)
        workitems.button_draft()
        workitems.process()
        self.assertTrue((workitems.state == "done"), "Follow-up item should be closed after process.")

        # I print workitem report.
        workitem_rp = Workitem.search([('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id), ('activity_id', '=', activity2)], limit=1)
        workitem_rp.preview()

        # I cancel segmentation because of some activity.
        segment0.signal_workflow('state_cancel_set')

        # I check the segmentation is canceled.
        self.assertEqual(segment0.state, 'cancelled')

        # I reopen the segmentation.
        segment0.signal_workflow('state_draft_set')
        segment0.signal_workflow('state_running_set')

        # I check the segment on Running mode after started.
        self.assertEqual(segment0.state, 'running')

        # I close segmentation After completion of all activity.
        segment0.signal_workflow('state_done_set')

        # I check the segmentation is done.
        self.assertEqual(segment0.state, 'done')

        # I close this campaign.
        partnerchannel.signal_workflow('state_done_set')

        # I check the campaing is done.
        self.assertEqual(partnerchannel.state, 'done')
