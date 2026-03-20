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
                'partner_email': '"Speaker" <speaker@test.example.com>',
                'partner_id': cls.event_customer.id,
            }, {
                'event_id': cls.event_0.id,
                'name': 'Partner (wrong email) and speaker email',
                'partner_email': '"Speaker" <speaker@test.example.com>',
                'partner_id': cls.event_customer_wrongemail.id,
            }, {
                'contact_email': '"Contact" <contact@test.example.com>',
                'event_id': cls.event_0.id,
                'name': 'Speaker and contact emails (no partner)',
                'partner_email': '"Speaker" <speaker@test.example.com>',
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
            # contact(_email) > partner_email (speaker info)
            self.tracks[2].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': self.event_customer.ids,
            },
            # contact wins (whatever email)
            self.tracks[3].id: {
                'email_cc': '', 'email_to': '',
                'partner_ids': self.event_customer.ids,
            },
            # wrong email -> fallback on valid speaker email
            self.tracks[4].id: {
                'email_cc': '', 'email_to': '"Speaker" <speaker@test.example.com>',
                'partner_ids': [],
            },
            # no partner: contact then speaker
            self.tracks[5].id: {
                'email_cc': '', 'email_to': '"Contact" <contact@test.example.com>',
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
                },
            ],
            # event with a partner, use it
            [
                {
                    'create_values': {},
                    'email': self.event_customer.email_normalized,
                    'name': self.event_customer.name,
                    'partner_id': self.event_customer.id,
                },
            ],
            # suggested take both partner and contact_email, as they are different
            [
                {
                    'create_values': {},
                    'email': self.event_customer.email_normalized,
                    'name': self.event_customer.name,
                    'partner_id': self.event_customer.id,
                }, {
                    'create_values': {},
                    'email': 'contact@test.example.com',
                    'name': 'Contact',
                    'partner_id': False,
                },
            ],
            # contact wins (whatever email)
            [
                {
                    'create_values': {},
                    'email': self.event_customer.email_normalized,
                    'name': self.event_customer.name,
                    'partner_id': self.event_customer.id,
                }, {
                    'create_values': {},
                    'email': 'speaker@test.example.com',
                    'name': 'Speaker',
                    'partner_id': False,
                },
            ],
            # partner with wrong email: add speaker as fallback
            [
                {
                    'create_values': {},
                    'email': self.event_customer_wrongemail.email_normalized,
                    'name': self.event_customer_wrongemail.name,
                    'partner_id': self.event_customer_wrongemail.id,
                }, {
                    'create_values': {},
                    'email': 'speaker@test.example.com',
                    'name': 'Speaker',
                    'partner_id': False,
                },
            ],
            # no partner: contact then speaker
            [
                {
                    'create_values': {},
                    'email': 'contact@test.example.com',
                    'name': 'Contact',
                    'partner_id': False,
                },
            ],
        ]

        suggested_all = tracks._message_get_suggested_recipients_batch()
        for track, expected in zip(tracks, expected_all, strict=True):
            suggested = suggested_all[track.id]
            with self.subTest(track_name=track.name):
                self.assertEqual(suggested, expected)
