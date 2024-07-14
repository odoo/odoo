# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tests import users
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.appointment.tests.common import AppointmentCommon

class AppointmentTestTracking(AppointmentCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.apt_type_follower = cls.env['res.partner'].create([{
            'name': 'Apt Type Follower',
            'country_id': cls.env.ref('base.be').id,
            'email': 'follower@test.lan',
            'mobile': '+32 499 90 23 09',
            'phone': '+32 81 212 220'
        }])
        cls.apt_type_bxls_2days.message_partner_ids = cls.apt_type_follower

        cls.appointment_attendee_ids = cls.env['res.partner'].create([{
            'name': f'Customer {attendee_indx}',
            'email': f'customer_{attendee_indx}@test.lan'
        } for attendee_indx in range(2)])

        cls.appointment_meeting_id = cls.env['calendar.event'].with_context(cls._test_context).create({
            'name': 'Test Tracking Appointment',
            'partner_ids': [Command.link(p) for p in cls.apt_manager.partner_id.ids + cls.appointment_attendee_ids.ids],
            'start': cls.reference_now,
            'stop': cls.reference_now + timedelta(hours=1),
            'user_id': cls.apt_manager.id,
            'appointment_type_id': cls.apt_type_bxls_2days.id
        }).with_context(mail_notrack=False)

    @freeze_time('2017-01-01')
    @users('apt_manager')
    def test_archive_message(self):
        """Check that we send cancelation notifications when archiving an appointment."""
        meeting = self.appointment_meeting_id
        self.assertGreater(meeting.start, datetime.now(), 'Test expects `datetime.now` to be before start of meeting')
        with self.mock_mail_gateway(), self.mock_mail_app():
            meeting.active = False
            self.flush_tracking()

        self.assertEqual(len(self._new_msgs), 2, 'Expected a tracking message and a cancelation template')
        self.assertTracking(
            self._new_msgs[0],
            [('active', 'boolean', True, False)]
        )
        self.assertEqual(self.ref('appointment.mt_calendar_event_canceled'), self._new_msgs[1].subtype_id.id,
                         'Expected a template cancelation message')

        with self.mock_mail_gateway(), self.mock_mail_app():
            meeting.active = True
            self.flush_tracking()

        self.assertEqual(len(self._new_msgs), 1, 'Expected a tracking message')
        self.assertTracking(
            self._new_msgs[0],
            [('active', 'boolean', False, True)]
        )

    @freeze_time('2017-01-01')
    def test_cancel_meeting_message(self):
        """ Make sure appointments send a custom message on archival/cancellation """
        meeting = self.appointment_meeting_id
        self.assertGreater(meeting.start, datetime.now(), 'Test expects `datetime.now` to be before start of meeting')
        permanent_followers = self.apt_manager.partner_id + self.apt_type_follower
        self.assertEqual(meeting.partner_ids, self.apt_manager.partner_id + self.appointment_attendee_ids,
                         'Manager and attendees should be there')
        self.assertEqual(meeting.message_partner_ids, permanent_followers + self.appointment_attendee_ids,
                         'All attendees and concerned users should be followers')

        with self.mock_mail_gateway(), self.mock_mail_app():
            meeting.with_context(mail_notify_force_send=True).action_cancel_meeting(self.appointment_attendee_ids[0].ids)
            self.flush_tracking()

        self.assertEqual(meeting.partner_ids, self.apt_manager.partner_id + self.appointment_attendee_ids[1],
                         'Manager and only one attendee should remain')
        self.assertEqual(meeting.message_partner_ids,
                         permanent_followers + self.appointment_attendee_ids[1],
                         'Only one attendee should be following anymore')

        self.assertEqual(len(self._new_msgs), 1, 'Should be a single message for the cancelation')
        self.assertMessageFields(self._new_msgs, {
            'body': f'<p>Appointment canceled by: {self.appointment_attendee_ids[0].display_name}</p>',
            'notification_ids': self.env['mail.notification'],
            'subtype_id': self.env.ref('mail.mt_note'),
        })
        with self.mock_mail_gateway(), self.mock_mail_app():
            meeting.with_user(self.apt_manager).action_cancel_meeting(self.appointment_attendee_ids[1].ids)
            self.flush_tracking()

        self.assertEqual(meeting.partner_ids, self.apt_manager.partner_id, 'Only the manager should remain')
        self.assertEqual(meeting.message_partner_ids, permanent_followers,
                         'None of the attendees should be following anymore')

        self.assertEqual(len(self._new_msgs), 1, 'Should be a message saying who canceled')
        self.assertMessageFields(self._new_msgs[0], {
            'body': f'<p>Appointment canceled by: {self.appointment_attendee_ids[1].display_name}</p>',
            'notification_ids': self.env['mail.notification'],
            'subtype_id': self.env.ref('mail.mt_note'),
        })
