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
        cls.location_a, cls.location_b, cls.location_c = cls.env['event.track.location'].create([
            {'name': 'Location A'}, {'name': 'Location B'}, {'name': 'Location C'},
        ])
        cls.speaker_1, cls.speaker_2 = cls.env['res.partner'].create([
            {'name': 'Speaker 1'}, {'name': 'Speaker 2'},
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

    def _track(self, name, hours_from_start, duration, speaker=None, **vals):
        return self.env['event.track'].create({
            'name': name,
            'event_id': self.event_0.id,
            'date': self.start + timedelta(hours=hours_from_start),
            'duration': duration,
            'partner_id': speaker.id if speaker else False,
            **vals,
        })

    def _check(self, track, expected, location=False, speaker=False):
        track.invalidate_recordset()
        self.assertEqual(track.conflicting_track_ids, expected, track.name)
        self.assertEqual(track.has_conflict, bool(expected), track.name)
        self.assertEqual(track.has_location_conflict, location, track.name)
        self.assertEqual(track.has_speaker_conflict, speaker, track.name)

    def test_location_conflict(self):
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 0.5, 1, location_id=self.location_a.id)
        self._check(track_1, track_2, location=True)
        self._check(track_2, track_1, location=True)

    def test_speaker_conflict_across_locations(self):
        track_1 = self._track('T1', 0, 1, self.speaker_1, location_id=self.location_a.id)
        track_2 = self._track('T2', 0.5, 1, self.speaker_1, location_id=self.location_b.id)
        self._check(track_1, track_2, speaker=True)
        self._check(track_2, track_1, speaker=True)

    def test_location_and_speaker_conflict(self):
        track_1 = self._track('T1', 0, 2, self.speaker_1, location_id=self.location_a.id)
        track_2 = self._track('T2', 1, 1, self.speaker_1, location_id=self.location_a.id)
        self._check(track_1, track_2, location=True, speaker=True)
        self._check(track_2, track_1, location=True, speaker=True)

    def test_no_conflict(self):
        # back-to-back in the same location: end == start is not an overlap
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 1, 1, location_id=self.location_a.id)
        # same time, different location and speaker
        track_3 = self._track('T3', 0, 1, self.speaker_2, location_id=self.location_b.id)
        # same speaker, different time
        track_4 = self._track('T4', 5, 1, self.speaker_2, location_id=self.location_c.id)
        # same time, nothing booked
        track_5 = self._track('T5', 0, 1)
        for track in track_1 | track_2 | track_3 | track_4 | track_5:
            self._check(track, self.env['event.track'])

    def test_location_scoped_to_event(self):
        track_1 = self._track('T1', 0, 1, self.speaker_1, location_id=self.location_a.id)
        same_location = self._track(
            'Same location', 0, 1, location_id=self.location_a.id, event_id=self.other_event.id)
        same_speaker = self._track(
            'Same speaker', 0, 1, self.speaker_1, location_id=self.location_b.id,
            event_id=self.other_event.id)
        self._check(same_location, self.env['event.track'])
        self._check(same_speaker, track_1, speaker=True)
        self._check(track_1, same_speaker, speaker=True)

    def test_extra_location_conflict(self):
        """ A track shown in several locations keeps each of them busy. """
        keynote = self._track(
            'Keynote', 0, 1, location_id=self.location_a.id, extra_location_ids=[(6, 0, self.location_b.ids)])
        overflow_talk = self._track('Overflow talk', 0.5, 1, location_id=self.location_b.id)
        other_room = self._track('Other room', 0, 1, location_id=self.location_c.id)
        self._check(keynote, overflow_talk, location=True)
        self._check(overflow_talk, keynote, location=True)
        self._check(other_room, self.env['event.track'])
        self.assertEqual(
            self.env['event.track'].search([
                ('id', 'in', (keynote | overflow_talk | other_room).ids), ('has_conflict', '=', True),
            ]),
            keynote | overflow_talk)

    def test_shared_extra_location_conflict(self):
        """ Two tracks retransmitted into the same location at the same time. """
        track_1 = self._track(
            'T1', 0, 1, location_id=self.location_a.id, extra_location_ids=[(6, 0, self.location_c.ids)])
        track_2 = self._track(
            'T2', 0.5, 1, location_id=self.location_b.id, extra_location_ids=[(6, 0, self.location_c.ids)])
        self._check(track_1, track_2, location=True)
        self._check(track_2, track_1, location=True)

    def test_extra_location_scoped_to_event(self):
        keynote = self._track(
            'Keynote', 0, 1, location_id=self.location_a.id, extra_location_ids=[(6, 0, self.location_b.ids)])
        other_event_talk = self._track(
            'Other event', 0, 1, location_id=self.location_b.id, event_id=self.other_event.id)
        self._check(keynote, self.env['event.track'])
        self._check(other_event_talk, self.env['event.track'])

    def test_finished_tracks_ignored(self):
        past_start = -24 * 30  # hours: 23 days ago
        track_1 = self._track('Past 1', past_start, 1, self.speaker_1, location_id=self.location_a.id)
        track_2 = self._track('Past 2', past_start, 1, self.speaker_1, location_id=self.location_a.id)
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
        self._check(track_1, track_2, location=True)
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
            self.assertTrue(form.has_location_conflict)
            # warning only: saving is not blocked
        self.assertTrue(self.env['event.track'].search_count([('name', '=', 'New talk')]))

    def test_action_view_conflicting_tracks(self):
        track_1 = self._track('T1', 0, 1, location_id=self.location_a.id)
        track_2 = self._track('T2', 0.5, 1, location_id=self.location_a.id)
        action = track_1.action_view_conflicting_tracks()
        self.assertEqual(self.env['event.track'].search(action['domain']), track_1 | track_2)
        self.assertFalse(action['context']['create'])
