# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.event.tests.common import TestEventCommon
from odoo.addons.website.models.website_visitor import WebsiteVisitor


class TestTrackSuggestion(TestEventCommon):
    def test_track_suggestion(self):
        [location_1, location_2] = self.env['event.track.location'].create([
            {'name': 'Location 1'},
            {'name': 'Location 2'},
        ])

        [tag_1, tag_2, tag_3, tag_4] = self.env['event.track.tag'].create([
            {'name': 'Tag 1'}, {'name': 'Tag 2'}, {'name': 'Tag 3'}, {'name': 'Tag 4'}
        ])

        date = fields.Datetime.from_string(datetime.now().strftime('%Y-%m-%d %H:00:00'))
        [track_1, track_2, track_3, track_4, track_5, track_6] = self.env['event.track'].create([{
            'name': 'Track 1',
            'location_id': location_1.id,
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_2.id)],
            'date': date + timedelta(hours=-1),
            'youtube_video_url': 'fake_url'
        }, {
            'name': 'Track 2',
            'location_id': location_2.id,
            'event_id': self.event_0.id,
            'date': date,
            'youtube_video_url': 'fake_url'
        }, {
            'name': 'Track 3',
            'location_id': location_2.id,
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_3.id), (4, tag_4.id)],
            'date': date,
            'youtube_video_url': 'fake_url'
        }, {
            'name': 'Track 4',
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_2.id)],
            'date': date,
            'youtube_video_url': 'fake_url'
        }, {
            'name': 'Track 5',
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_3.id)],
            'wishlisted_by_default': True,
            'date': date,
            'youtube_video_url': 'fake_url'
        }, {
            'name': 'Track 6',
            'location_id': location_1.id,
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_3.id)],
            'date': date,
            'youtube_video_url': 'fake_url'
        }])

        visitor = self.env['website.visitor'].create({
            'name': 'Visitor',
            'partner_id': self.env.user.partner_id.id
        })
        visitor_track = self.env['event.track.visitor'].create({
            'visitor_id': visitor.id,
            'track_id': track_3.id
        })

        with patch.object(WebsiteVisitor, '_get_visitor_from_request', lambda *args, **kwargs: visitor):
            track_suggestion = track_1._get_next_track_suggestion()
            self.assertEqual(track_3, track_suggestion,
                'Returned track should be the manually wishlisted one')
            visitor_track.unlink()

            track_suggestion = track_1._get_next_track_suggestion()
            self.assertEqual(track_5, track_suggestion,
                'Returned track should be the default wishlisted one')
            self.env['event.track'].search([]).write({'wishlisted_by_default': False})

            track_suggestion = track_1._get_next_track_suggestion()
            self.assertEqual(track_4, track_suggestion,
                'Returned track should the one with the most common tags')
            self.env['event.track'].search([]).write({'tag_ids': [(5,)]})

            track_suggestion = track_1._get_next_track_suggestion()
            self.assertEqual(track_6, track_suggestion,
                'Returned track should the one with the most common tags')
            self.env['event.track'].search([]).write({'location_id': False})

            track_suggestion = track_1._get_next_track_suggestion()
            self.assertTrue(track_suggestion in [track_2, track_3, track_4, track_5, track_6],
                "Returned track should the a random one (but not the one we're trying to get suggestion for)")
