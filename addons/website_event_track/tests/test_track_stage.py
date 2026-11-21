# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged, users


@tagged('event_track_stage')
class TestTrackStage(TestEventOnlineCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_stages = cls.env['event.event']._get_default_track_stages()
        cls.stage_proposal = cls.env.ref('website_event_track.event_track_stage0')
        cls.stage_published = cls.env.ref('website_event_track.event_track_stage3')
        cls.stage_refused = cls.env.ref('website_event_track.event_track_stage4')
        cls.stage_custom_1, cls.stage_custom_2 = cls.env['event.track.stage'].create([
            {'name': 'Custom Review', 'sequence': 0},
            {'name': 'Custom Accepted', 'sequence': 10},
        ])
        cls.event_type_custom = cls.env['event.type'].create({
            'name': 'Custom Workflow',
            'track_stage_ids': [(6, 0, (cls.stage_custom_1 | cls.stage_custom_2).ids)],
        })

    def test_default_stages(self):
        """ Standard stages for events without template, template stages otherwise """
        self.assertEqual(len(self.default_stages), 6)
        self.assertEqual(self.event_0.track_stage_ids, self.default_stages)

        event_custom = self.env['event.event'].create({
            'name': 'Custom',
            'event_type_id': self.event_type_custom.id,
        })
        self.assertEqual(event_custom.track_stage_ids, self.stage_custom_1 | self.stage_custom_2)

        # template without stages: default stages
        event_type_empty = self.env['event.type'].create({'name': 'No Stages'})
        event_empty_type = self.env['event.event'].create({
            'name': 'Empty Type',
            'event_type_id': event_type_empty.id,
        })
        self.assertEqual(event_empty_type.track_stage_ids, self.default_stages)

        # changing the template keeps the stages used by tracks
        track = self.env['event.track'].create({'name': 'Track', 'event_id': self.event_0.id})
        self.assertEqual(track.stage_id, self.stage_proposal)
        self.event_0.event_type_id = self.event_type_custom
        self.assertEqual(
            self.event_0.track_stage_ids,
            self.stage_custom_1 | self.stage_custom_2 | self.stage_proposal,
        )

    def test_event_copy_shares_stages(self):
        self.event_0.track_stage_ids = self.stage_custom_1 | self.stage_published
        event_copy = self.event_0.copy()
        self.assertEqual(event_copy.track_stage_ids, self.stage_custom_1 | self.stage_published)

    @users('user_eventmanager')
    def test_track_stage_compute(self):
        event = self.event_0.with_env(self.env)
        event_custom = self.env['event.event'].create({
            'name': 'Custom',
            'event_type_id': self.event_type_custom.id,
        })

        # first unfolded stage of the event, as done by the proposal controller
        track = self.env['event.track'].sudo().create({'name': 'Proposal', 'event_id': event.id})
        self.assertEqual(track.stage_id, self.stage_proposal)
        track_custom = self.env['event.track'].create({'name': 'Custom', 'event_id': event_custom.id})
        self.assertEqual(track_custom.stage_id, self.stage_custom_1)

        # moving to an event without the stage resets it
        track.event_id = event_custom
        self.assertEqual(track.stage_id, self.stage_custom_1)
        # moving to an event having the stage keeps it
        event.track_stage_ids |= self.stage_custom_1
        track.event_id = event
        self.assertEqual(track.stage_id, self.stage_custom_1)

        # folded stages are not used as default, whatever their sequence
        stage_folded = self.env['event.track.stage'].create({'name': 'Folded', 'sequence': -1, 'fold': True})
        event_fold = self.env['event.event'].create({'name': 'Fold'})
        event_fold.track_stage_ids = stage_folded | self.stage_published
        self.assertEqual(event_fold._get_default_track_stage(), self.stage_published)

    @users('user_eventmanager')
    def test_track_stage_linked_to_event(self):
        """ A stage given explicitly is linked to the event of the track """
        event = self.event_0.with_env(self.env)
        event.track_stage_ids = self.stage_proposal
        track = self.env['event.track'].create({
            'name': 'Track',
            'event_id': event.id,
            'stage_id': self.stage_custom_2.id,
        })
        self.assertEqual(track.stage_id, self.stage_custom_2)
        self.assertEqual(event.track_stage_ids, self.stage_proposal | self.stage_custom_2)

        track.stage_id = self.stage_published
        self.assertEqual(event.track_stage_ids, self.stage_proposal | self.stage_custom_2 | self.stage_published)

        # event without any stage: tracks get a default stage, linked to the event
        event_nostage = self.env['event.event'].create({'name': 'No Stage'})
        event_nostage.track_stage_ids = False
        track = self.env['event.track'].create({'name': 'Track', 'event_id': event_nostage.id})
        self.assertEqual(track.stage_id, self.stage_proposal)
        self.assertEqual(event_nostage.track_stage_ids, self.stage_proposal)

    @users('user_eventmanager')
    def test_track_stage_removal(self):
        """ A stage holding tracks of an event cannot be removed from it """
        event = self.event_0.with_env(self.env)
        stage_custom_1 = self.stage_custom_1.with_env(self.env)
        event.track_stage_ids = self.stage_proposal | stage_custom_1
        track = self.env['event.track'].create({
            'name': 'Track',
            'event_id': event.id,
            'stage_id': stage_custom_1.id,
        })
        track.action_archive()

        with self.assertRaises(ValidationError):
            event.track_stage_ids = self.stage_proposal
        with self.assertRaises(ValidationError):
            stage_custom_1.event_ids = False

        # unused stage can be removed, from both sides
        event.track_stage_ids = stage_custom_1
        self.assertEqual(event.track_stage_ids, stage_custom_1)
        self.stage_proposal.with_env(self.env).event_ids |= event
        self.stage_proposal.with_env(self.env).event_ids -= event
        self.assertEqual(event.track_stage_ids, stage_custom_1)

    def test_track_stage_read_group_expand(self):
        event = self.event_0
        event.track_stage_ids = self.stage_proposal | self.stage_custom_1
        event_other = self.env['event.event'].create({
            'name': 'Other',
            'event_type_id': self.event_type_custom.id,
        })
        self.env['event.track'].create({
            'name': 'Track',
            'event_id': event_other.id,
            'stage_id': self.stage_custom_2.id,
        })

        Track = self.env['event.track'].with_context(default_event_id=event.id, read_group_expand=True)
        groups = Track.formatted_read_group([('event_id', '=', event.id)], ['stage_id'], ['__count'])
        self.assertEqual(
            {group['stage_id'][0] for group in groups},
            set((self.stage_proposal | self.stage_custom_1).ids),
            'Only the stages of the event should be displayed',
        )

        # without event in context, only stages holding tracks
        groups = self.env['event.track'].with_context(read_group_expand=True).formatted_read_group([('event_id', '=', event_other.id)], ['stage_id'], ['__count'])
        self.assertEqual({group['stage_id'][0] for group in groups}, set(self.stage_custom_2.ids))

    @users('user_eventuser')
    def test_track_stage_access(self):
        """ Event users can read stages, only managers manage them """
        self.assertTrue(self.stage_proposal.with_env(self.env).name)
        with self.assertRaises(AccessError):
            self.env['event.track.stage'].create({'name': 'Forbidden'})
        with self.assertRaises(AccessError):
            self.stage_proposal.with_env(self.env).name = 'Forbidden'
