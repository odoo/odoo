# -*- coding: utf-8 -*-

from openerp.tests import common


class TestMarketingCampaign(common.TransactionCase):

    def test_00_marketing_campaign_tests(self):

        # In order to test process of compaign, I start compaign.
        partnerchannel = self.env.ref(
            'marketing_campaign.marketing_campaign_openerppartnerchannel')
        partnerchannel.signal_workflow('state_running_set')

        # I check the campaign on Running mode after started.
        self.assertEqual(partnerchannel.state, 'running')

        # I start this segment after assinged campaign.
        segment0 = self.env.ref(
            'marketing_campaign.marketing_campaign_segment0')
        segment0.signal_workflow('state_running_set')

        # I check the segment on Running mode after started.
        self.assertEqual(segment0.state, 'running')

        # I synchronized segment manually to see all step of activity and
        # process covered on this campaign.
        assert segment0.date_next_sync, 'Next Synchronization date is not calculated.'
        segment0.synchroniz()

        # I cancel Marketing Workitems.
        workitem = self.env['marketing.campaign.workitem']
        workitem_rs1 = workitem.search(
            [('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id)])
        workitem_rs1.button_cancel()
        record1 = workitem_rs1[0]
        assert record1.state == 'cancelled' or record1.state == 'done', 'Marketing Workitem shoud be in cancel state.'

        # I set Marketing Workitems in draft state.
        workitem_rs1.button_draft()
        assert record1.state == 'todo' or record1.state == 'done', 'Marketing Workitem shoud be in draft state.'

        # I process follow-up of first activity.
        workitem_rs2 = workitem.search([('segment_id', '=', segment0.id),
                                        ('campaign_id', '=', partnerchannel.id), ('activity_id', '=', segment0.id)])
        assert workitem_rs2.ids, 'Follow-up item is not created for first activity.'
        assert workitem_rs2[0].res_name, 'Resource Name is not defined.'
        workitem_rs2.process()
        assert workitem_rs2[
            0].state == "done", "Follow-up item should be closed after process."

        # I check follow-up detail of second activity after process of first
        # activity.
        activity1 = self.env.ref(
            'marketing_campaign.marketing_campaign_activity_1')
        workitem_rs3 = workitem.search([('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id), (
            'activity_id', '=', activity1.id)])

        assert workitem_rs3.ids, 'Follow - up item is not created for second activity.'

        # Now I increase credit limit of customer
        self.env.ref('base.res_partner_2').write({'credit_limit': 41000})

        # I process follow-up of second activity after set draft.
        workitem_rs3.button_draft()
        workitem_rs3.process()
        assert workitem_rs3[
            0].state == "done", "Follow-up item should be closed after process."

        # I check follow-up detail of third activity after process of second
        # activity.
        activity2 = self.env.ref(
            'marketing_campaign.marketing_campaign_activity_2')
        workitem_rs4 = workitem.search([('segment_id', '=', segment0.id), ('campaign_id', '=', partnerchannel.id), (
            'activity_id', '=', activity2.id)])
        assert workitem_rs4.ids, 'Follow-up item is not created for third activity.'

        # Now I increase credit limit of customer
        self.env.ref('base.res_partner_2').write({'credit_limit': 151000})

        # I process follow-up of third activity after set draft.
        workitem_rs4.button_draft()
        workitem_rs4.process()
        assert workitem_rs4[
            0].state == "done", "Follow-up item should be closed after process."

        # I print workitem report.
        workitem_rs4[0].preview()

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
