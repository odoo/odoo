# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import json
from datetime import timedelta

from freezegun import freeze_time
from PIL import Image

from odoo import fields
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import HttpCase, tagged, users
from odoo.tools import BinaryBytes

from odoo.addons.website_event.tests.common import TestEventOnlineCommon


def _image(color):
    with io.BytesIO() as image_io:
        Image.new('RGB', (4, 4), color=color).save(image_io, 'PNG')
        return BinaryBytes(image_io.getvalue())


@tagged('event_track_speaker', 'post_install', '-at_install')
class TestTrackSpeaker(TestEventOnlineCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event_0.write({'website_published': True, 'website_track': True})
        cls.company = cls.env['res.partner'].create({'name': 'ACME', 'is_company': True})
        cls.jane = cls.env['res.partner'].create({
            'name': 'Jane Speaker',
            'function': 'CTO',
            'parent_id': cls.company.id,
            'email': 'jane@example.com',
            'phone': '+32 470 00 00 01',
        })
        cls.track = cls.env['event.track'].create({
            'name': 'Panel discussion',
            'event_id': cls.event_0.id,
            'date': fields.Datetime.now() + timedelta(days=5, hours=1),
            'description': '<p>About the panel</p>',
            'speaker_ids': [
                Command.create({'name': 'Alice Host', 'function': 'Host', 'image': _image('red')}),
                Command.create({'partner_id': cls.jane.id}),
                Command.create({'name': 'Bob Manual', 'function': 'Freelance', 'email': 'bob@example.com'}),
            ],
        })

    def test_speaker_defaults_from_partner(self):
        _alice, jane, bob = self.track.speaker_ids
        self.assertEqual(
            (jane.name, jane.function, jane.company_name, jane.email, jane.phone),
            ('Jane Speaker', 'CTO', 'ACME', 'jane@example.com', '+32 470 00 00 01'))
        self.assertEqual(jane.tag_line, 'Jane Speaker, CTO at ACME')
        self.assertEqual((bob.name, bob.function, bob.partner_id), ('Bob Manual', 'Freelance', self.env['res.partner']))
        # values can be overridden for the talk without touching the contact
        jane.function = 'Keynote host'
        self.assertEqual(self.jane.function, 'CTO')
        # a contact only fills the empty values
        bob.partner_id = self.jane
        self.assertEqual(
            (bob.name, bob.function, bob.email, bob.phone),
            ('Bob Manual', 'Freelance', 'bob@example.com', '+32 470 00 00 01'))

    def test_speakers_are_equal(self):
        """ Every speaker is described the same way, whatever its position:
        the sequence only orders their display. """
        track = self.track
        self.assertEqual(track.speaker_count, 3)
        self.assertEqual(track.speaker_tag_line, 'Alice Host, Host / Jane Speaker, CTO at ACME / Bob Manual, Freelance')

        # reordering the speakers only reorders the tag line
        alice, jane, bob = track.speaker_ids
        jane.sequence, bob.sequence, alice.sequence = 1, 2, 3
        self.assertEqual(track.speaker_tag_line, 'Jane Speaker, CTO at ACME / Bob Manual, Freelance / Alice Host, Host')

        # a speaker without name is left out of the tag line
        track.speaker_ids = [Command.create({'email': 'anonymous@example.com'})]
        self.assertEqual(track.speaker_count, 4)
        self.assertEqual(track.speaker_tag_line, 'Jane Speaker, CTO at ACME / Bob Manual, Freelance / Alice Host, Host')
        self.assertEqual(track.speaker_ids[-1].display_name, 'anonymous@example.com')

        # removing every speaker clears the tag line
        track.speaker_ids = [Command.clear()]
        self.assertEqual(track.speaker_count, 0)
        self.assertFalse(track.speaker_tag_line)

    @users('user_eventuser')
    def test_speaker_management_event_user(self):
        track = self.track.with_env(self.env)
        track.speaker_ids = [Command.delete(track.speaker_ids[0].id)]
        self.assertEqual(track.speaker_ids.mapped('name'), ['Jane Speaker', 'Bob Manual'])
        self.assertEqual(track.speaker_tag_line, 'Jane Speaker, CTO at ACME / Bob Manual, Freelance')

    def test_track_copy(self):
        copy = self.track.copy()
        self.assertEqual(copy.speaker_ids.mapped('name'), ['Alice Host', 'Jane Speaker', 'Bob Manual'])
        self.assertNotEqual(copy.speaker_ids, self.track.speaker_ids)
        self.assertEqual(copy.speaker_ids[0].image.content, self.track.speaker_ids[0].image.content)
        self.assertEqual(copy.speaker_tag_line, self.track.speaker_tag_line)

    def test_public_access_follows_track_publication(self):
        public = self.env.ref('base.public_user')
        speakers = self.track.speaker_ids.with_user(public)
        self.track.is_published = False
        with self.assertRaises(AccessError):
            speakers.mapped('name')
        self.track.is_published = True
        speakers.invalidate_recordset()
        self.assertEqual(speakers.mapped('name'), ['Alice Host', 'Jane Speaker', 'Bob Manual'])

    @users('user_eventmanager')
    def test_speakers_are_not_recipients(self):
        """ Speakers only describe the talk: the contact of the track is the
        only one suggested, and a contact created from the chatter is linked
        to the track, never to a speaker. """
        self.track.user_id = False
        track = self.track.with_env(self.env)
        self.assertFalse(track._message_get_suggested_recipients())

        track.partner_id = self.jane
        self.assertEqual(
            [(recipient['partner_id'], recipient['email']) for recipient in track._message_get_suggested_recipients()],
            [(self.jane.id, 'jane@example.com')])

        track.partner_id = False
        track.contact_email = 'bob@example.com'
        bob_partner = self.env['res.partner'].sudo().create({'name': 'Bob Manual', 'email': 'bob@example.com'})
        track.message_post(body='Welcome', partner_ids=bob_partner.ids)
        self.assertEqual(track.partner_id, bob_partner)
        self.assertFalse(track.speaker_ids.filtered(lambda speaker: speaker.name == 'Bob Manual').partner_id)

    def test_proposal_creates_speaker(self):
        self.event_0.website_track_proposal = True
        self.authenticate(None, None)
        response = self.url_open(f'/event/{self.event_0.id}/track_proposal/post', data={
            'track_name': 'My proposal',
            'description': 'About my talk',
            'tags': '',
            'speaker_name': 'Proposed Speaker',
            'speaker_email': 'proposed@example.com',
            'speaker_phone': '0456001122',
            'speaker_function': 'Developer',
            'speaker_biography': 'Born in...',
            'add_contact_information': 'on',
            'contact_name': 'Proposal Contact',
            'contact_email': 'contact@example.com',
            'contact_phone': '0456998877',
            'csrf_token': self.csrf_token(),
        })
        self.assertEqual(json.loads(response.text), {'success': True})
        track = self.env['event.track'].search([('name', '=', 'My proposal')])
        self.assertEqual(len(track), 1)
        speaker = track.speaker_ids
        self.assertEqual(len(speaker), 1)
        self.assertEqual(
            (speaker.name, speaker.email, speaker.phone, speaker.function, speaker.partner_id),
            ('Proposed Speaker', 'proposed@example.com', '0456001122', 'Developer', self.env['res.partner']))
        self.assertIn('Born in...', speaker.biography)
        # the proposal contact is the contact of the track, not a speaker
        self.assertEqual(
            (track.partner_id.name, track.partner_id.email, track.contact_email, track.contact_phone),
            ('Proposal Contact', 'contact@example.com', 'contact@example.com', '0456998877'))

    def test_proposal_speaker_details_as_contact(self):
        """ Without additional contact information, the speaker details are
        the contact details of the track: the speaker is not a recipient. """
        self.event_0.website_track_proposal = True
        self.authenticate(None, None)
        response = self.url_open(f'/event/{self.event_0.id}/track_proposal/post', data={
            'track_name': 'My solo proposal',
            'description': 'About my talk',
            'tags': '',
            'speaker_name': 'Solo Speaker',
            'speaker_email': 'solo@example.com',
            'speaker_phone': '0456001122',
            'csrf_token': self.csrf_token(),
        })
        self.assertEqual(json.loads(response.text), {'success': True})
        track = self.env['event.track'].search([('name', '=', 'My solo proposal')])
        self.assertFalse(track.partner_id)
        self.assertEqual((track.contact_email, track.contact_phone), ('solo@example.com', '0456001122'))
        self.assertEqual(track.speaker_ids.email, 'solo@example.com')

    def test_website_track_page(self):
        self.track.is_published = True
        response = self.url_open(f'/event/{self.event_0.id}/track/{self.track.id}')
        self.assertEqual(response.status_code, 200)
        for name in ('Alice Host', 'Jane Speaker', 'Bob Manual'):
            self.assertIn(name, response.text)
        self.assertEqual(response.text.count('o_wevent_track_speaker'), 3)
        agenda = self.url_open(f'/event/{self.event_0.id}/agenda')
        self.assertIn('Alice Host, Host / Jane Speaker, CTO at ACME / Bob Manual, Freelance', agenda.text)

    def test_event_jsonld_performers(self):
        self.track.is_published = True
        with freeze_time(self.reference_now):
            performers = self.event_0._prepare_jsonld_vals()['performer']
        self.assertEqual(
            [performer['name'] for performer in performers],
            ['Alice Host', 'Jane Speaker', 'Bob Manual'])
