from odoo import Command
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from odoo.tests import tagged, users


@tagged('post_install', '-at_install', 'mail_flow', 'mail_tools')
class TestTrackMailFeatures(TestEventOnlineCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event_customer_wrongemail = cls.env['res.partner'].create({
            'email': 'wrong',
            'name': 'Wrong Emails',
        })
        cls.tracks = cls.env['event.track'].with_user(cls.user_eventmanager).create([
            {
                'contact_email': 'not.partner@test.example.com',
                'event_id': cls.event_0.id,
                'name': 'Email Ony',
            }, {
                'event_id': cls.event_0.id,
                'name': 'Partner',
                'partner_id': cls.event_customer.id,
            }, {
                'contact_email': '"Contact" <contact@test.example.com>',
                'event_id': cls.event_0.id,
                'name': 'Partner and contact',
                'partner_id': cls.event_customer.id,
            }, {
                'contact_email': False,
                'event_id': cls.event_0.id,
                'name': 'Partner (no contact_email) and speaker email',
                'speaker_ids': [Command.create({'email': '"Speaker" <speaker@test.example.com>'})],
                'partner_id': cls.event_customer.id,
            }, {
                'event_id': cls.event_0.id,
                'name': 'Partner (wrong email) and speaker email',
                'speaker_ids': [Command.create({'email': '"Speaker" <speaker@test.example.com>'})],
                'partner_id': cls.event_customer_wrongemail.id,
            }, {
                'contact_email': '"Contact" <contact@test.example.com>',
                'event_id': cls.event_0.id,
                'name': 'Speaker and contact emails (no partner)',
                'speaker_ids': [Command.create({'email': '"Speaker" <speaker@test.example.com>'})],
            }, {
                'event_id': cls.event_0.id,
                'name': 'Several speakers and a contact',
                'partner_id': cls.event_customer.id,
                'speaker_ids': [
                    Command.create({'email': '"Speaker" <speaker@test.example.com>'}),
                    Command.create({'partner_id': cls.event_customer_wrongemail.id}),
                    Command.create({'name': 'Speaker without email'}),
                ],
            }, {
                'event_id': cls.event_0.id,
                'name': 'Speakers only (no contact)',
                'speaker_ids': [
                    Command.create({'email': '"Speaker" <speaker@test.example.com>'}),
                    Command.create({'partner_id': cls.event_customer.id}),
                ],
            },
        ])

    @users('user_eventmanager')
    def test_track_default_recipients(self):
        """ Test track default recipients """
        tracks = self.tracks.with_user(self.env.user)
        defaults = tracks._message_get_default_recipients()
        expected_all = {
            self.tracks[0].id: {
                'email_cc': '', 'email_to': 'not.partner@test.example.com',
                'partner_ids': [],
            },
            # partner wins, being the contact
            self.tracks[1].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': self.event_customer.ids,
            },
            # partner > contact_email
            self.tracks[2].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': self.event_customer.ids,
            },
            # contact wins, speakers are never recipients
            self.tracks[3].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': self.event_customer.ids,
            },
            # wrong email: the contact stays, no fallback on the speaker email
            self.tracks[4].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': self.event_customer_wrongemail.ids,
            },
            # no partner: contact only
            self.tracks[5].id: {
                'email_cc': '', 'email_to': '"Contact" <contact@test.example.com>',
                'partner_ids': [],
            },
            # several speakers: the contact only
            self.tracks[6].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': self.event_customer.ids,
            },
            # speakers without contact: nobody
            self.tracks[7].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': [],
            },
        }

        for track in tracks:
            expected = expected_all.get(track.id)
            with self.subTest(track_name=track.name):
                self.assertEqual(defaults[track.id], expected)

    @users('user_eventmanager')
    def test_track_suggested_recipients(self):
        """ Test track suggested recipients """
        tracks = self.tracks.with_user(self.env.user)
        expected_all = [
            [
                {
                    'create_values': {},
                    'email': 'not.partner@test.example.com',
                    'name': '',
                    'partner_id': False,
                    'recipient_type': 'to',
                },
            ],
            # event with a partner, use it
            [
                {
                    'create_values': {},
                    'email': self.event_customer.email_normalized,
                    'name': self.event_customer.name,
                    'partner_id': self.event_customer.id,
                    'recipient_type': 'to',
                },
            ],
            # suggested take both partner and contact_email, as they are different
            [
                {
                    'create_values': {},
                    'email': self.event_customer.email_normalized,
                    'name': self.event_customer.name,
                    'partner_id': self.event_customer.id,
                    'recipient_type': 'to',
                }, {
                    'create_values': {},
                    'email': 'contact@test.example.com',
                    'name': 'Contact',
                    'partner_id': False,
                    'recipient_type': 'to',
                },
            ],
            # contact wins, speakers are never suggested
            [
                {
                    'create_values': {},
                    'email': self.event_customer.email_normalized,
                    'name': self.event_customer.name,
                    'partner_id': self.event_customer.id,
                    'recipient_type': 'to',
                },
            ],
            # partner with wrong email: no fallback on the speaker email
            [
                {
                    'create_values': {},
                    'email': self.event_customer_wrongemail.email_normalized,
                    'name': self.event_customer_wrongemail.name,
                    'partner_id': self.event_customer_wrongemail.id,
                    'recipient_type': 'to',
                },
            ],
            # no partner: contact only
            [
                {
                    'create_values': {},
                    'email': 'contact@test.example.com',
                    'name': 'Contact',
                    'partner_id': False,
                    'recipient_type': 'to',
                },
            ],
            # several speakers: the contact only
            [
                {
                    'create_values': {},
                    'email': self.event_customer.email_normalized,
                    'name': self.event_customer.name,
                    'partner_id': self.event_customer.id,
                    'recipient_type': 'to',
                },
            ],
            # speakers without contact: nobody
            [],
        ]

        suggested_all = tracks._message_get_suggested_recipients_batch()
        for track, expected in zip(tracks, expected_all, strict=True):
            suggested = suggested_all[track.id]
            with self.subTest(track_name=track.name):
                self.assertEqual(suggested, expected)
