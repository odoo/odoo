# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase


class TestMergeUtmCampaign(SavepointCase):
    def setUp(self):
        super(TestMergeUtmCampaign, self).setUp()
        self.utm_source = self.env['utm.source'].create({
            'name': 'utm source'
        })
        self.utm_medium = self.env['utm.medium'].create({
            'name': 'utm medium'
        })
        self.utm_campaign_1 = self.env['utm.campaign'].create({
            'name': 'utm campaign 1'
        })
        self.utm_campaign_2 = self.env['utm.campaign'].create({
            'name': 'utm campaign 2'
        })
        self.utm_campaign_3 = self.env['utm.campaign'].create({
            'name': 'utm campaign 3'
        })
        self.link_tracker_1 = self.env['link.tracker'].create({
            'url': 'www.dodd.com',
            'campaign_id': self.utm_campaign_1.id,
            'medium_id': self.utm_medium.id,
            'source_id': self.utm_source.id
        })
        self.link_tracker_2 = self.env['link.tracker'].create({
            'url': 'www.dodd.com',
            'campaign_id': self.utm_campaign_2.id,
            'medium_id': self.utm_medium.id,
            'source_id': self.utm_source.id
        })
        self.link_tracker_3 = self.env['link.tracker'].create({
            'url': 'www.odoo.com',
            'campaign_id': self.utm_campaign_3.id,
            'medium_id': self.utm_medium.id,
            'source_id': self.utm_source.id
        })
        self.link_tracker_click_1 = self.env['link.tracker.click'].create({
            'link_id': self.link_tracker_1.id
        })
        self.link_tracker_click_2 = self.env['link.tracker.click'].create({
            'link_id': self.link_tracker_2.id
        })
        self.link_tracker_click_3 = self.env['link.tracker.click'].create({
            'link_id': self.link_tracker_3.id
        })

    def test_merge_unique(self):
        """ Merge 2 campaigns and check that everything is correctly cleaned up.
        Link trackers should be cleaned in this case since they're not unique
        anymore (see 'link_tracker.py'#_clean_duplicates) """
        link_codes_1 = self.link_tracker_1.link_code_ids
        link_clicks_1 = self.link_tracker_1.link_click_ids
        link_codes_2 = self.link_tracker_2.link_code_ids
        link_clicks_2 = self.link_tracker_2.link_click_ids
        total_click_count = self.link_tracker_1.campaign_id.click_count + self.link_tracker_2.campaign_id.click_count

        (self.utm_campaign_1 + self.utm_campaign_2)._merge_utm_campaigns(self.utm_campaign_1)

        link_tracker = self.env['link.tracker'].search([('campaign_id', '=', self.utm_campaign_1.id)])
        link_tracker_empty = self.env['link.tracker'].search([('campaign_id', '=', self.utm_campaign_2.id)])

        self.assertFalse(self.utm_campaign_2.active,
            "After merging utm.campaigns, unneeded campaigns should be archived. ")
        self.assertEqual(self.utm_campaign_2.reference_utm_campaign_id, self.utm_campaign_1,
            "After merging utm.campaigns, deactivated utm.campaign should refer to the merged campaign. ")
        self.assertEqual(len(link_tracker.ids), 1,
            "After merging utm.campaigns, duplicate link.trackers should be unlinked.")
        self.assertEqual(len(link_tracker_empty.ids), 0,
            "After merging utm.campaigns, no link.tracker link to deactivated utm.campaign.")
        self.assertFalse(self.link_tracker_2 in self.env['link.tracker'].search([]),
            "After merging utm.campaigns, duplicate link.trackers should be unlinked.")
        self.assertEqual(link_tracker.link_code_ids, link_codes_1 + link_codes_2,
            "After merging utm.campaigns, link.tracker.code of duplicate link.tracker should be redirected to the remaining one.")
        self.assertEqual(link_tracker.link_click_ids, link_clicks_1 + link_clicks_2,
            "After merging utm.campaigns, link.tracker.click of duplicate link.tracker should be redirected to the remaining one.")
        self.assertEqual(self.link_tracker_1.campaign_id.click_count, total_click_count,
            "After merging utm.campaigns, click count should be the sum of all merged campaigns.")

    def test_merge_nonunique(self):
        """ Merge 2 campaigns and check that everything unrelated remains
        unchanged. Nothing but the campaign_id should be changed since the
        unique constraint can still be met.
        (see 'link_tracker.py'#_clean_duplicates) """
        link_codes_3 = self.link_tracker_3.link_code_ids
        link_clicks_3 = self.link_tracker_3.link_click_ids

        (self.utm_campaign_1 + self.utm_campaign_3)._merge_utm_campaigns(self.utm_campaign_1)

        link_trackers = self.env['link.tracker'].search([('campaign_id', '=', self.utm_campaign_1.id)])

        self.assertEqual(self.link_tracker_1 + self.link_tracker_3, link_trackers,
            "After merging utm.campaigns, link_trackers should be redirected to the merged campaign.")
        self.assertEqual(self.link_tracker_3.link_code_ids, link_codes_3,
            "After merging utm.campaigns, link.tracker.code remains unchanged.")
        self.assertEqual(self.link_tracker_3.link_click_ids, link_clicks_3,
            "After merging utm.campaigns, link.tracker.click remains unchanged.")
