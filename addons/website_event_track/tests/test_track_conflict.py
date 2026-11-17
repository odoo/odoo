# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.website_event.tests.common import TestEventOnlineCommon


@tagged('post_install', '-at_install', 'event_track_conflict')
class TestTrackConflict(TestEventOnlineCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location_a, cls.location_b = cls.env['event.track.location'].create([
            {'name': 'Location A'}, {'name': 'Location B'},
        ])
        cls.cancel_stage = cls.env['event.track.stage'].create({
            'name': 'Cancelled (test)', 'is_cancel': True,
        })
        cls.other_event = cls.env['event.event'].create({
            'name': 'Other Event',
            'date_begin': cls.event_0.date_begin,
            'date_end': cls.event_0.date_end,
        })
        # in the future: tracks that are already over are ignored
        cls.start = fields.Datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=7)

    def _track(self, name, hours_from_start, duration, **vals):
        return self.env['event.track'].create({
            'name': name,
            'event_id': self.event_0.id,
            'date': self.start + timedelta(hours=hours_from_start),
            'duration': duration,
            **vals,
        })

    def _check(self, track, expected):
        track.invalidate_recordset()
        self.assertEqual(track.conflicting_track_ids, expected, track.name)
        self.assertEqual(track.has_conflict, bool(expected), track.name)

    def test_location_conflict(self):
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 0.5, 1, location_id=self.location_a.id)
        self._check(track_1, track_2)
        self._check(track_2, track_1)

    def test_no_conflict(self):
        # back-to-back in the same location: end == start is not an overlap
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 1, 1, location_id=self.location_a.id)
        # same time, different location
        track_3 = self._track('T3', 0, 1, location_id=self.location_b.id)
        # same time, no location
        track_4 = self._track('T4', 0, 1)
        for track in track_1 | track_2 | track_3 | track_4:
            self._check(track, self.env['event.track'])

    def test_location_scoped_to_event(self):
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        other_event_track = self._track(
            'Same location', 0, 1, location_id=self.location_a.id, event_id=self.other_event.id)
        self._check(track_1, self.env['event.track'])
        self._check(other_event_track, self.env['event.track'])

    def test_finished_tracks_ignored(self):
        past_start = -24 * 30  # hours: 23 days ago
        track_1 = self._track('Past 1', past_start, 1, location_id=self.location_a.id)
        track_2 = self._track('Past 2', past_start, 1, location_id=self.location_a.id)
        self._check(track_1, self.env['event.track'])
        self._check(track_2, self.env['event.track'])
        self.assertFalse(
            self.env['event.track'].search([('id', 'in', (track_1 | track_2).ids), ('has_conflict', '=', True)]))

    def test_cancelled_and_archived_ignored(self):
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 0, 1, location_id=self.location_a.id)
        normal_stage = track_2.stage_id
        track_2.stage_id = self.cancel_stage
        self._check(track_1, self.env['event.track'])
        self._check(track_2, self.env['event.track'])
        track_2.stage_id = normal_stage
        self._check(track_1, track_2)
        track_2.active = False
        self._check(track_1, self.env['event.track'])

    def test_search_has_conflict(self):
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 0.5, 1, location_id=self.location_a.id)
        track_3 = self._track('T3', 5, 1, location_id=self.location_a.id)
        tracks = track_1 | track_2 | track_3
        self.assertEqual(tracks.filtered_domain([('has_conflict', '=', True)]), track_1 | track_2)
        self.assertEqual(
            self.env['event.track'].search([('id', 'in', tracks.ids), ('has_conflict', '=', True)]),
            track_1 | track_2)
        self.assertEqual(
            self.env['event.track'].search([('id', 'in', tracks.ids), ('has_conflict', '=', False)]),
            track_3)

    def test_form_warning(self):
        self._track('T1', 0, 1, location_id=self.location_a.id)
        with Form(self.env['event.track']) as form:
            form.name = 'New talk'
            form.event_id = self.event_0
            form.date = self.start + timedelta(minutes=30)
            form.duration = 1
            form.location_id = self.location_b
            self.assertFalse(form.has_conflict)
            form.location_id = self.location_a
            self.assertTrue(form.has_conflict)
            # warning only: saving is not blocked
        self.assertTrue(self.env['event.track'].search_count([('name', '=', 'New talk')]))

    def test_action_view_conflicting_tracks(self):
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 0.5, 1, location_id=self.location_a.id)
        action = track_1.action_view_conflicting_tracks()
        self.assertEqual(self.env['event.track'].search(action['domain']), track_1 | track_2)
        self.assertFalse(action['context']['create'])
