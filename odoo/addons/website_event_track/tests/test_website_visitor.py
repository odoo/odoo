# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTests
from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from odoo.tests import tagged


@tagged('website_visitor')
class WebsiteVisitorTestsEventTrack(TestEventOnlineCommon, WebsiteVisitorTests):

    def test_clean_inactive_visitors_event_track(self):
        """ Visitors that have wishlisted tracks should not be deleted even if not connected
        recently. """
        track_1 = self.env['event.track'].create({
            'name': 'Track 1',
            'event_id': self.event_0.id,
        })

        active_visitors = self.env['website.visitor'].create([{
            'name': 'Wishlister Alex',
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'last_connection_datetime': datetime.now() - timedelta(days=8),
            'access_token': 'f9d2b93591d6f602e5e8afa238e35a6c',
            'event_track_visitor_ids': [(0, 0, {
                'track_id': track_1.id,
                'is_wishlisted': True
            })]
        }])

        self._test_unlink_old_visitors(self.env['website.visitor'], active_visitors)

    def test_link_to_visitor_event_track(self):
        """ Same as parent's 'test_link_to_visitor' except we also test that tracks
        that are wishlisted are merged into main visitor. """

        [track_1, track_2] = self.env['event.track'].create([{
            'name': 'Track 1',
            'event_id': self.event_0.id,
        }, {
            'name': 'Track 2',
            'event_id': self.event_0.id,
        }])

        [main_visitor, linked_visitor] = self.env['website.visitor'].create([
            self._prepare_main_visitor_data(),
            self._prepare_linked_visitor_data()
        ])

        self.env['event.track.visitor'].create([{
            'visitor_id': main_visitor.id,
            'track_id': track_1.id,
            'is_wishlisted': True,
        }, {
            'visitor_id': linked_visitor.id,
            'track_id': track_2.id,
            'is_wishlisted': True,
        }])

        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        # wishlisted tracks of both visitors should be merged into main one
        self.assertEqual(
            main_visitor.event_track_wishlisted_ids,
            track_1 | track_2)
