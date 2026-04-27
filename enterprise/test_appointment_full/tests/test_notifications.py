from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.google_calendar.models.res_users import User as GoogleUser
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.microsoft_calendar.models.res_users import User as MsftUser
from odoo.addons.microsoft_calendar.tests.common import TestCommon as MsftTestCommon
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService

from odoo.tests import users


class TestAppointmentNotificationCommon(AppointmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attendee_ids = cls.env['res.partner'].create([
            {'name': f'p{n}', 'email': f'p{n}@test.lan'} for n in range(2)
        ])

        # admin is just a user that follows the appointment type and is making the booking
        # apt_user is the person assigned to the booking, not a follower of the apt type.
        # apt_manager is just a follower of the appointment type who doesn't otherwise have anything to do with the booking
        cls.apt_type_bxls_2days.message_partner_ids = cls.user_admin.partner_id + cls.apt_manager.partner_id
        (cls.user_admin + cls.apt_manager + cls.apt_user).notification_type = 'email'

        cls.apt_type_resource.booked_mail_template_id = cls._create_template('calendar.attendee', {
            'body_html': 'Thanks for booking!',
            'subject': 'Thanks for booking, {{object.common_name}}',
        })

    def _create_event(self, additional_values=None):
        additional_values = additional_values or {}
        return self._create_meetings(
            self.apt_user, [(datetime(2020, 2, 1, 10), datetime(2020, 2, 1, 11), False)],
            appointment_type_id=self.apt_type_bxls_2days.id, suppress_mail=False, partners=self.attendee_ids,
            meeting_values={'name': 'Test Notification Appointment', 'appointment_status': 'booked'} | additional_values
        )


class TestAppointmentNotificationsMail(TestAppointmentNotificationCommon):
    @freeze_time('2020-02-01 09:00:00')
    @users('admin')
    def test_appointment_notification_templates_mail(self):
        """Check that booking and cancelation notifications are sent to the right people when only using mail."""
        with self.mock_mail_gateway():
            appointment = self._create_event()
            self.env.flush_all()
            self.cr.precommit.run()
        booked_mail = self.assertMailMail(
            self.apt_manager.partner_id + self.apt_user.partner_id,
            'sent',
            author=self.apt_user.partner_id,  # author: synchronized with email_from of template
            email_values={
                'subject': 'Appointment Booked: Bxls Appt Type',
            },
            fields_values={
                'subtype_id': self.env.ref('appointment.mt_calendar_event_booked'),
                'notified_partner_ids': self.apt_manager.partner_id + self.apt_user.partner_id,
            },
        )
        self.assertFalse(
            any(mail.subtype_id == self.env.ref('appointment.mt_calendar_event_booked') for mail in self._new_mails - booked_mail),
            "Only internal users should receive the booking notification mail",
        )
        with self.mock_mail_gateway():
            appointment.with_context(mail_notify_author=True).action_archive()
            self.env.flush_all()
            self.cr.precommit.run()
        # one email for users, including followers of the apt type
        self.assertMailMail(
            (self.apt_manager.partner_id + self.apt_user.partner_id),
            'sent',
            author=self.apt_user.partner_id,
            email_values={
                'subject': 'Appointment Canceled: Bxls Appt Type',
            },
            fields_values={
                'subtype_id': self.env.ref('appointment.mt_calendar_event_canceled'),
            },
        )
        # one email for other attendees
        self.assertMailMail(
            appointment.partner_ids - self.apt_user.partner_id,
            'sent',
            author=self.apt_user.partner_id,
            email_values={
                'subject': 'Appointment Canceled: Bxls Appt Type',
            },
            fields_values={
                'subtype_id': self.env.ref('appointment.mt_calendar_event_canceled'),
            },
        )
        self.assertMailMail(appointment.partner_ids - appointment.partner_id, 'sent', author=appointment.partner_id)


class TestSyncOdoo2GoogleMail(TestSyncGoogle, TestAppointmentNotificationCommon):
    @freeze_time('2020-02-01 09:00:00')
    @patch.object(GoogleUser, '_get_google_calendar_token', lambda user: 'some-token')
    @users('admin')
    def test_appointment_notification_templates_gcalendar(self):
        """Check that booking and cancelation notifications are sent to the right people when syncing with google calendar."""
        self.env.user.res_users_settings_id._set_google_auth_tokens('some-token', '123', 10000)
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_google_sync():
            appointment = self._create_event()
            appointment.google_id = 'test_google_id'  # would normally be set by insert
            self.env.flush_all()
            self.cr.precommit.run()
        self.assertGoogleEventInserted({'id': False, 'summary': 'Test Notification Appointment'})
        self.assertMailMail(
            self.apt_manager.partner_id + self.apt_user.partner_id,
            'sent',
            author=self.apt_user.partner_id,  # author: synchronized with email_from of template
            email_values={
                'subject': 'Appointment Booked: Bxls Appt Type',
            },
            fields_values={
                'subtype_id': self.env.ref('appointment.mt_calendar_event_booked'),
            },
        )
        self.assertNotSentEmail(appointment.partner_ids - self.apt_user.partner_id)
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_google_sync():
            appointment.action_archive()
            self.env.flush_all()
            self.cr.precommit.run()
        self.assertGoogleEventPatched('test_google_id', {'status': 'cancelled'}, timeout=3)
        self.assertMailMail(
            self.apt_manager.partner_id + self.apt_user.partner_id,
            'sent',
            author=self.apt_user.partner_id,  # author: synchronized with email_from of template
            email_values={
                'subject': 'Appointment Canceled: Bxls Appt Type',
            },
            fields_values={
                'subtype_id': self.env.ref('appointment.mt_calendar_event_canceled'),
            },
        )
        self.assertNotSentEmail(appointment.partner_ids - self.apt_user.partner_id)


class TestAppointmentNotificationsMicrosoftCalendar(MsftTestCommon, TestAppointmentNotificationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_public = mail_new_test_user(
            cls.env, login='user_public', groups='base.group_public', name='Public User'
        )
        cls.public_user_booking_partner = cls.env['res.partner'].create({
            'name': 'Booking attendee',
            'email': 'booking.attendee@test.lan',
        })

    def setUp(self):
        super().setUp()
        # attendee user in parent class is created in setUp
        sync_paused_attendee = self.attendee_user.copy(default={
            'email': 'ms.sync.paused@test.lan',
            'login': 'ms_sync_paused_user',
        })
        sync_paused_attendee.microsoft_synchronization_stopped = True

    @freeze_time('2020-02-01 09:00:00')
    @patch.object(MsftUser, '_get_microsoft_calendar_token', lambda user: 'some-token')
    @users('admin')
    def test_appointment_cancel_notification_templates_msftcalendar(self):
        """Check that booking and cancelation notifications are sent to the right people when syncing with microsoft calendar."""
        with self.mock_mail_gateway(), patch.object(MicrosoftCalendarService, 'insert') as mock_insert:
            mock_insert.return_value = ('test_msft_id', 'test_msft_uid')
            appointment = self._create_event()
            appointment.microsoft_id = 'test_msft_id'  # would normally be set by insert
            self.env.flush_all()
            self.cr.precommit.run()
            self.env.cr.postcommit.run()
        mock_insert.assert_called_once()
        self.assertMailMail(
            self.apt_manager.partner_id + self.apt_user.partner_id,
            'sent',
            author=self.apt_user.partner_id,  # author: synchronized with email_from of template
            email_values={
                'subject': 'Appointment Booked: Bxls Appt Type',
            },
            fields_values={
                'subtype_id': self.env.ref('appointment.mt_calendar_event_booked'),
            },
        )
        self.assertNotSentEmail(appointment.partner_ids - self.apt_user.partner_id)
        with self.mock_mail_gateway(), patch.object(MicrosoftCalendarService, 'delete') as mock_delete:
            appointment.action_archive()
            self.env.flush_all()
            self.cr.precommit.run()
            self.env.cr.postcommit.run()
        mock_delete.assert_called_once_with('test_msft_id', token='some-token', timeout=5)
        self.assertMailMail(
            self.apt_manager.partner_id + self.apt_user.partner_id,
            'sent',
            author=self.apt_user.partner_id,  # author: synchronized with email_from of template
            email_values={
                'subject': 'Appointment Canceled: Bxls Appt Type',
            },
            fields_values={
                'subtype_id': self.env.ref('appointment.mt_calendar_event_canceled'),
            },
        )
        self.assertNotSentEmail(appointment.partner_ids - self.apt_user.partner_id)

    @freeze_time('2020-02-01 09:00:00')
    @users('mike@organizer.com', 'john@attendee.com', 'ms_sync_paused_user', 'user_public')
    @patch.object(
        MsftUser, '_get_microsoft_calendar_token',
        lambda user: user.login not in ['user_public', 'john@attendee.com'] and 'some-token'
    )
    def test_sync_or_email_resource_appointment(self):
        """Check that resource appointments are synced even if there is no organizer, unless the attendee is not syncing."""
        for with_organizer in [True, False]:
            with self.subTest(with_organizer=with_organizer):
                is_public = self.env.user == self.user_public
                booking_partner = self.env.user.partner_id if not is_public else self.public_user_booking_partner
                expected_author = booking_partner if not is_public else self.user_public.partner_id
                if with_organizer:
                    expected_author = self.organizer_user.partner_id
                with self.mock_mail_gateway(mail_unlink_sent=False), patch.object(MicrosoftCalendarService, 'insert') as mock_insert:
                    mock_insert.return_value = ('1', '1')
                    meeting = self.env['calendar.event'].with_context(mail_notify_author=True).sudo(is_public).create({
                        'appointment_type_id': self.apt_type_resource.id,
                        'name': f'Resource Appointment {booking_partner.name}',
                        'partner_ids': booking_partner.ids,
                        'start': datetime.now() + timedelta(days=1),
                        'stop': datetime.now() + timedelta(days=1, hours=1),
                        'user_id': with_organizer and self.organizer_user.id,
                    })
                    self.env.flush_all()
                    self.cr.precommit.run()
                    self.cr.postcommit.run()
                # synced with the organizer (who can always sync in this test), but checked against the create user
                if meeting._check_microsoft_sync_status() and self.env.user._get_microsoft_sync_status() == "sync_active":
                    mock_insert.assert_called_once()
                    # no mail sent to non-organizer partners, if any exists
                    if meeting.partner_ids - meeting.partner_id:
                        self.assertNotSentEmail(meeting.partner_ids - meeting.partner_id)
                else:
                    mock_insert.assert_not_called()
                    self.assertMailMail(
                        booking_partner, 'sent',
                        author=expected_author,
                        fields_values={'subject': f'Thanks for booking, {booking_partner.name}'}
                    )
                if with_organizer:
                    self.assertMailMail(
                        meeting.partner_id, 'sent',
                        author=expected_author,
                        fields_values={'subject': 'Appointment Booked: Test'}
                    )
